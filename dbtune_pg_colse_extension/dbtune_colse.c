#include "postgres.h"
#include "fmgr.h"
#include "lib/stringinfo.h"
#include "optimizer/paths.h"
#include "tcop/tcopprot.h"
#include "utils/builtins.h"
#include "utils/guc.h"

#include "executor/executor.h"
#include "nodes/plannodes.h"
#include "tcop/utility.h"

#include <curl/curl.h>
#include <ctype.h>
#include <errno.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

PG_MODULE_MAGIC;

static bool dbtune_colse_enabled = true;
/* Kept for backward compatibility; replacement is now controlled by
 * dbtune.colse_enabled alone. */
static bool dbtune_colse_replace_pg_ce = false;
static bool dbtune_colse_log_decisions = false;
static char *colse_service_url = NULL;
static int colse_timeout_ms = 1500;

static ExecutorStart_hook_type prev_ExecutorStart = NULL;
static ProcessUtility_hook_type prev_ProcessUtility = NULL;
static set_rel_pathlist_hook_type prev_set_rel_pathlist = NULL;

typedef struct CurlString {
  char *ptr;
  size_t len;
} CurlString;

static void init_string(CurlString *s) {
  s->len = 0;
  s->ptr = palloc(1);
  s->ptr[0] = '\0';
}

static size_t writefunc(void *ptr, size_t size, size_t nmemb, void *userdata) {
  size_t real_size = size * nmemb;
  CurlString *s = (CurlString *)userdata;
  s->ptr = repalloc(s->ptr, s->len + real_size + 1);
  memcpy(s->ptr + s->len, ptr, real_size);
  s->len += real_size;
  s->ptr[s->len] = '\0';
  return real_size;
}

static char *escape_json_string(const char *input) {
  StringInfoData buf;
  const char *p = NULL;

  initStringInfo(&buf);
  for (p = input; *p; p++) {
    switch (*p) {
    case '\"':
      appendStringInfoString(&buf, "\\\"");
      break;
    case '\\':
      appendStringInfoString(&buf, "\\\\");
      break;
    case '\b':
      appendStringInfoString(&buf, "\\b");
      break;
    case '\f':
      appendStringInfoString(&buf, "\\f");
      break;
    case '\n':
      appendStringInfoString(&buf, "\\n");
      break;
    case '\r':
      appendStringInfoString(&buf, "\\r");
      break;
    case '\t':
      appendStringInfoString(&buf, "\\t");
      break;
    default:
      if ((unsigned char)*p < 0x20)
        appendStringInfo(&buf, "\\u%04x", *p);
      else
        appendStringInfoChar(&buf, *p);
    }
  }
  return buf.data;
}

static char *send_query_to_colse(const char *sql_text) {
  CURL *curl = NULL;
  CURLcode rc;
  CurlString response;
  struct curl_slist *headers = NULL;
  char *escaped_sql = NULL;
  StringInfo json = NULL;

  if (!dbtune_colse_enabled || colse_service_url == NULL)
    return NULL;

  curl = curl_easy_init();
  if (!curl)
    return NULL;

  init_string(&response);
  headers = curl_slist_append(headers, "Content-Type: application/json");
  escaped_sql = escape_json_string(sql_text);

  json = makeStringInfo();
  appendStringInfo(json, "{\"query\":\"%s\"}", escaped_sql);

  curl_easy_setopt(curl, CURLOPT_URL, colse_service_url);
  curl_easy_setopt(curl, CURLOPT_POSTFIELDS, json->data);
  curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
  curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, writefunc);
  curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
  curl_easy_setopt(curl, CURLOPT_TIMEOUT_MS, (long)colse_timeout_ms);

  rc = curl_easy_perform(curl);
  if (rc != CURLE_OK)
    elog(WARNING, "[DBTune CoLSE] HTTP request failed: %s",
         curl_easy_strerror(rc));
  else
    elog(LOG, "[DBTune CoLSE] response: %s", response.ptr);

  curl_slist_free_all(headers);
  curl_easy_cleanup(curl);

  return response.ptr;
}

static bool parse_cardinality_estimate(const char *response, double *estimate) {
  const char *key = "\"cardinality_estimate\"";
  const char *pos = NULL;
  const char *num_start = NULL;
  char *num_end = NULL;
  double parsed = 0.0;

  if (!response || !estimate)
    return false;

  pos = strstr(response, key);
  if (!pos)
    return false;

  pos = strchr(pos, ':');
  if (!pos)
    return false;
  pos++;

  while (*pos && isspace((unsigned char)*pos))
    pos++;
  if (*pos == '"')
    pos++;

  num_start = pos;
  errno = 0;
  parsed = strtod(num_start, &num_end);
  if (num_end == num_start || errno != 0 || !isfinite(parsed) || parsed < 0.0)
    return false;

  *estimate = parsed;
  return true;
}

static bool fetch_colse_cardinality(const char *sql_text, double *estimate) {
  char *response = NULL;
  bool ok = false;
  double parsed = 0.0;

  if (!sql_text || !estimate)
    return false;

  response = send_query_to_colse(sql_text);
  if (!response)
    return false;

  ok = parse_cardinality_estimate(response, &parsed);
  pfree(response);

  if (!ok)
    return false;

  *estimate = parsed;
  return true;
}

static const char *extract_select_for_colse(const char *query_text) {
  const char *p = NULL;
  const char *sel = NULL;

  if (!query_text)
    return NULL;

  p = query_text;
  while (*p && isspace((unsigned char)*p))
    p++;

  if (pg_strncasecmp(p, "explain", 7) != 0)
    return query_text;

  sel = strcasestr(p, "select");
  if (!sel)
    return query_text;

  return sel;
}

static void maybe_send_query(const char *query_text) {
  if (!query_text || !dbtune_colse_enabled)
    return;

  if (strstr(query_text, "dbtune_colse_estimate(") != NULL)
    return;

  (void)send_query_to_colse(query_text);
}

static bool query_is_colse_replacement_eligible(PlannerInfo *root,
                                                RelOptInfo *rel, Index rti,
                                                RangeTblEntry *rte) {
  Query *query = NULL;
  RangeTblRef *rtr = NULL;

  if (!dbtune_colse_enabled)
    return false;
  if (!root || !root->parse || !rel || !rte)
    return false;
  if (rel->reloptkind != RELOPT_BASEREL || rte->rtekind != RTE_RELATION)
    return false;

  query = root->parse;
  if (query->commandType != CMD_SELECT)
    return false;
  if (query->setOperations != NULL || query->cteList != NIL ||
      query->hasSubLinks || query->hasAggs || query->hasWindowFuncs ||
      query->hasTargetSRFs || query->groupClause != NIL ||
      query->distinctClause != NIL || query->havingQual != NULL ||
      query->limitOffset != NULL || query->limitCount != NULL)
    return false;

  if (!query->jointree || list_length(query->jointree->fromlist) != 1)
    return false;
  if (!IsA(linitial(query->jointree->fromlist), RangeTblRef))
    return false;

  rtr = (RangeTblRef *)linitial(query->jointree->fromlist);
  if (rtr->rtindex != rti)
    return false;

  return true;
}

static void override_rel_rows(RelOptInfo *rel, double rows) {
  ListCell *lc = NULL;

  rel->rows = rows;
  foreach (lc, rel->pathlist) {
    Path *path = lfirst_node(Path, lc);
    if (path)
      path->rows = rows;
  }
  foreach (lc, rel->partial_pathlist) {
    Path *path = lfirst_node(Path, lc);
    if (path)
      path->rows = rows;
  }
  foreach (lc, rel->cheapest_parameterized_paths) {
    Path *path = lfirst_node(Path, lc);
    if (path)
      path->rows = rows;
  }
  if (rel->cheapest_startup_path)
    rel->cheapest_startup_path->rows = rows;
  if (rel->cheapest_total_path)
    rel->cheapest_total_path->rows = rows;
  if (rel->cheapest_unique_path)
    rel->cheapest_unique_path->rows = rows;
}

static void colse_set_rel_pathlist(PlannerInfo *root, RelOptInfo *rel,
                                   Index rti, RangeTblEntry *rte) {
  double estimate = 0.0;
  double clamped_rows = 1.0;
  const char *query_text = extract_select_for_colse(debug_query_string);

  if (prev_set_rel_pathlist)
    prev_set_rel_pathlist(root, rel, rti, rte);

  if (!query_is_colse_replacement_eligible(root, rel, rti, rte)) {
    if (dbtune_colse_log_decisions)
      elog(LOG, "[DBTune CoLSE] planner replacement skipped (ineligible)");
    return;
  }
  if (!query_text || query_text[0] == '\0') {
    if (dbtune_colse_log_decisions)
      elog(LOG, "[DBTune CoLSE] planner replacement skipped (no query text)");
    return;
  }
  if (!fetch_colse_cardinality(query_text, &estimate)) {
    if (dbtune_colse_log_decisions)
      elog(LOG, "[DBTune CoLSE] planner replacement skipped (fetch failed)");
    return;
  }

  clamped_rows = Max(1.0, estimate);
  override_rel_rows(rel, clamped_rows);
  if (dbtune_colse_log_decisions)
    elog(LOG, "[DBTune CoLSE] planner replacement applied rows=%.3f",
         clamped_rows);
}

static void colse_ExecutorStart(QueryDesc *queryDesc, int eflags) {
  if (queryDesc && queryDesc->sourceText)
    maybe_send_query(queryDesc->sourceText);

  if (prev_ExecutorStart)
    prev_ExecutorStart(queryDesc, eflags);
  else
    standard_ExecutorStart(queryDesc, eflags);
}

static void colse_ProcessUtility(PlannedStmt *pstmt, const char *queryString,
                                 bool readOnlyTree,
                                 ProcessUtilityContext context,
                                 ParamListInfo params,
                                 QueryEnvironment *queryEnv, DestReceiver *dest,
                                 QueryCompletion *qc) {
  maybe_send_query(queryString);

  if (prev_ProcessUtility)
    prev_ProcessUtility(pstmt, queryString, readOnlyTree, context, params,
                        queryEnv, dest, qc);
  else
    standard_ProcessUtility(pstmt, queryString, readOnlyTree, context, params,
                            queryEnv, dest, qc);
}

void _PG_init(void);
void _PG_fini(void);
PG_FUNCTION_INFO_V1(dbtune_colse_estimate);

void _PG_init(void) {
  DefineCustomBoolVariable("dbtune.colse_enabled", "Enable CoLSE bridge.", NULL,
                           &dbtune_colse_enabled, true, PGC_SIGHUP, 0, NULL,
                           NULL, NULL);

  DefineCustomBoolVariable("dbtune.colse_replace_pg_ce",
                           "Deprecated compatibility flag. CoLSE replacement is "
                           "now controlled by dbtune.colse_enabled.",
                           NULL, &dbtune_colse_replace_pg_ce, false, PGC_SIGHUP,
                           0, NULL, NULL, NULL);

  DefineCustomBoolVariable("dbtune.colse_log_decisions",
                           "Log CoLSE planner replacement decisions.", NULL,
                           &dbtune_colse_log_decisions, false, PGC_SIGHUP, 0,
                           NULL, NULL, NULL);

  DefineCustomStringVariable(
      "dbtune.colse_service_url", "The CoLSE estimate service URL.", NULL,
      &colse_service_url, "http://colse_api:5060/colse/estimate", PGC_SIGHUP, 0,
      NULL, NULL, NULL);

  DefineCustomIntVariable("dbtune.colse_timeout_ms",
                          "HTTP timeout for CoLSE bridge in milliseconds.",
                          NULL, &colse_timeout_ms, 1500, 100, 60000, PGC_SIGHUP,
                          0, NULL, NULL, NULL);

  prev_ExecutorStart = ExecutorStart_hook;
  ExecutorStart_hook = colse_ExecutorStart;

  prev_ProcessUtility = ProcessUtility_hook;
  ProcessUtility_hook = colse_ProcessUtility;

  prev_set_rel_pathlist = set_rel_pathlist_hook;
  set_rel_pathlist_hook = colse_set_rel_pathlist;

  elog(LOG, "[DBTune CoLSE] hooks installed");
}

void _PG_fini(void) {
  ExecutorStart_hook = prev_ExecutorStart;
  ProcessUtility_hook = prev_ProcessUtility;
  set_rel_pathlist_hook = prev_set_rel_pathlist;
}

Datum dbtune_colse_estimate(PG_FUNCTION_ARGS) {
  text *sql_text = PG_GETARG_TEXT_PP(0);
  char *query = text_to_cstring(sql_text);
  char *response = send_query_to_colse(query);

  if (response == NULL)
    PG_RETURN_TEXT_P(cstring_to_text("colse request skipped"));
  PG_RETURN_TEXT_P(cstring_to_text(response));
}
