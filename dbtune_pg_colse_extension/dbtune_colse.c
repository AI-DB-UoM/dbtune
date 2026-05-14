#include "postgres.h"
#include "fmgr.h"
#include "lib/stringinfo.h"
#include "utils/builtins.h"
#include "utils/guc.h"

#include "executor/executor.h"
#include "nodes/plannodes.h"
#include "tcop/utility.h"

#include <curl/curl.h>
#include <string.h>

PG_MODULE_MAGIC;

static bool dbtune_colse_enabled = true;
static char *colse_service_url = NULL;
static int colse_timeout_ms = 1500;

static ExecutorStart_hook_type prev_ExecutorStart = NULL;
static ProcessUtility_hook_type prev_ProcessUtility = NULL;

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

static void maybe_send_query(const char *query_text) {
  if (!query_text || !dbtune_colse_enabled)
    return;

  if (strstr(query_text, "dbtune_colse_estimate(") != NULL)
    return;

  (void)send_query_to_colse(query_text);
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
  DefineCustomBoolVariable("dbtune_colse_enabled", "Enable CoLSE bridge.", NULL,
                           &dbtune_colse_enabled, true, PGC_SIGHUP, 0, NULL,
                           NULL, NULL);

  DefineCustomStringVariable(
      "dbtune_colse_service_url", "The CoLSE estimate service URL.", NULL,
      &colse_service_url, "http://colse_api:5060/colse/estimate", PGC_SIGHUP, 0,
      NULL, NULL, NULL);

  DefineCustomIntVariable("dbtune_colse_timeout_ms",
                          "HTTP timeout for CoLSE bridge in milliseconds.",
                          NULL, &colse_timeout_ms, 1500, 100, 60000, PGC_SIGHUP,
                          0, NULL, NULL, NULL);

  prev_ExecutorStart = ExecutorStart_hook;
  ExecutorStart_hook = colse_ExecutorStart;

  prev_ProcessUtility = ProcessUtility_hook;
  ProcessUtility_hook = colse_ProcessUtility;

  elog(LOG, "[DBTune CoLSE] hooks installed");
}

void _PG_fini(void) {
  ExecutorStart_hook = prev_ExecutorStart;
  ProcessUtility_hook = prev_ProcessUtility;
}

Datum dbtune_colse_estimate(PG_FUNCTION_ARGS) {
  text *sql_text = PG_GETARG_TEXT_PP(0);
  char *query = text_to_cstring(sql_text);
  char *response = send_query_to_colse(query);

  if (response == NULL)
    PG_RETURN_TEXT_P(cstring_to_text("colse request skipped"));
  PG_RETURN_TEXT_P(cstring_to_text(response));
}
