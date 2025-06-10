#include "postgres.h"
#include "fmgr.h"
#include "utils/guc.h"
#include "utils/builtins.h"
#include "lib/stringinfo.h"
#include <curl/curl.h>
#include <unistd.h>

#include "tcop/utility.h"
#include "miscadmin.h"

#include "tcop/utility.h"        // for ProcessUtility_hook_type
#include "executor/executor.h"   // for ExecutorStart_hook_type, QueryDesc
#include "nodes/plannodes.h"     // for PlannedStmt
#include "parser/parse_type.h"   // optional, but useful

/* a required macro in every PostgreSQL C extension.
It embeds a special "magic block" in the compiled shared object (.so) file */
PG_MODULE_MAGIC;

// static bool enable_dbtune_mab = false;
static char *mab_service_url = NULL;
static bool dbtune_mab_tuning = false;

/* Hook variables */
static ExecutorStart_hook_type prev_ExecutorStart = NULL;
static ProcessUtility_hook_type prev_ProcessUtility = NULL;

struct curl_string {
    char *ptr;
    size_t len;
};


static void init_string(struct curl_string *s) {
    s->len = 0;
    s->ptr = palloc(1);
    s->ptr[0] = '\0';
}

static size_t writefunc(void *ptr, size_t size, size_t nmemb, void *userdata) {
    size_t real_size = size * nmemb;
    struct curl_string *s = (struct curl_string *)userdata;
    s->ptr = repalloc(s->ptr, s->len + real_size + 1);
    memcpy(s->ptr + s->len, ptr, real_size);
    s->len += real_size;
    s->ptr[s->len] = '\0';
    return real_size;
}

static void send_query_to_mab(const char *sql_text) {
    CURL *curl = curl_easy_init();
    if (!curl) return;

    struct curl_string response;
    init_string(&response);

    struct curl_slist *headers = NULL;
    headers = curl_slist_append(headers, "Content-Type: application/json");

    StringInfo json = makeStringInfo();
    appendStringInfo(json, "{\"query\": \"%s\"}", sql_text);

    curl_easy_setopt(curl, CURLOPT_URL, mab_service_url);
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, json->data);
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, writefunc);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);

    curl_easy_perform(curl);
    curl_easy_cleanup(curl);
}

/* Hooked ExecutorStart */
static void my_ExecutorStart(QueryDesc *queryDesc, int eflags)
{
    if (queryDesc && queryDesc->sourceText) {
        elog(LOG, "[HOOK] Query: %s", queryDesc->sourceText);
        if (dbtune_mab_tuning && mab_service_url)
            send_query_to_mab(queryDesc->sourceText);
    }

    if (prev_ExecutorStart)
        prev_ExecutorStart(queryDesc, eflags);
    else
        standard_ExecutorStart(queryDesc, eflags);
}

/* Hooked ProcessUtility */
static void my_ProcessUtility(PlannedStmt *pstmt,
    const char *queryString,
    bool readOnlyTree,
    ProcessUtilityContext context,
    ParamListInfo params,
    QueryEnvironment *queryEnv,
    DestReceiver *dest,
    QueryCompletion *qc)
{
    elog(LOG, "[HOOK] Utility: %s", queryString);
    if (dbtune_mab_tuning && mab_service_url)
        send_query_to_mab(queryString);

    if (prev_ProcessUtility)
        prev_ProcessUtility(pstmt, queryString, readOnlyTree, context, params, queryEnv, dest, qc);
    else
        standard_ProcessUtility(pstmt, queryString, readOnlyTree, context, params, queryEnv, dest, qc);
}



void _PG_init(void);
void _PG_fini(void);
PG_FUNCTION_INFO_V1(dbtune_mab_tune);

/* Module load */
void _PG_init(void) {
    // DefineCustomBoolVariable("dbtune.enable_mab", "Enable DBTune MAB module.", NULL,
    //                          &enable_dbtune_mab, false, PGC_SUSET, 0, NULL, NULL, NULL);
    // DefineCustomStringVariable("dbtune.mab_service_url", "MAB service URL.", NULL,
    //                            &mab_service_url, "http://mab_api:5050/mab/tune_async", PGC_SUSET, 0, NULL, NULL, NULL);
    DefineCustomBoolVariable("dbtune_mab_tuning", "Enable MAB tuning globally", NULL,                         
                                &dbtune_mab_tuning, false, PGC_SIGHUP, 0,NULL, NULL, NULL);
    DefineCustomStringVariable("dbtune_mab_service_url", "MAB service URL.", NULL,
                                &mab_service_url, "http://mab_api:5050/mab/tune_async", PGC_SIGHUP, 0, NULL, NULL, NULL);

    prev_ExecutorStart = ExecutorStart_hook;
    ExecutorStart_hook = my_ExecutorStart;

    prev_ProcessUtility = ProcessUtility_hook;
    ProcessUtility_hook = my_ProcessUtility;

    elog(LOG, "pg_hook_logger loaded: hooks installed");
                                                            
}

/* Module unload */
void _PG_fini(void)
{
    ExecutorStart_hook = prev_ExecutorStart;
    ProcessUtility_hook = prev_ProcessUtility;

    elog(LOG, "pg_hook_logger unloaded: hooks removed");
}


static char *send_post_and_get_id(const char *json_body) {
    CURL *curl = curl_easy_init();
    if (!curl) elog(ERROR, "Failed to init curl");

    struct curl_slist *headers = NULL;
    headers = curl_slist_append(headers, "Content-Type: application/json");

    struct curl_string response;
    response.ptr = palloc(1);
    response.ptr[0] = '\0';
    response.len = 0;

    curl_easy_setopt(curl, CURLOPT_URL, mab_service_url);
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, json_body);
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, writefunc);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);

    CURLcode res = curl_easy_perform(curl);
    curl_easy_cleanup(curl);

    if (res != CURLE_OK)
        elog(ERROR, "curl_easy_perform failed: %s", curl_easy_strerror(res));

    char *start = strstr(response.ptr, "\"task_id\":");
    if (!start) elog(ERROR, "Response does not contain task_id");
    start = strchr(start, '"');
    start = strchr(start + 1, '"');
    char *end = strchr(start + 1, '"');
    *end = '\0';

    return pstrdup(start + 1);
}

static char *poll_until_done(const char *task_id) {
    CURL *curl = curl_easy_init();
    if (!curl) elog(ERROR, "Failed to init curl");

    struct curl_string response;
    response.ptr = palloc(1);
    response.ptr[0] = '\0';
    response.len = 0;

    StringInfo url = makeStringInfo();
    appendStringInfo(url, "http://mab_api:5050/mab/status/%s", task_id);

    int attempts = 0;
    while (attempts++ < 3600) {
        response.len = 0;
        response.ptr[0] = '\0';

        curl_easy_setopt(curl, CURLOPT_URL, url->data);
        curl_easy_setopt(curl, CURLOPT_HTTPGET, 1L);
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, writefunc);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);

        CURLcode res = curl_easy_perform(curl);
        if (res != CURLE_OK)
            elog(ERROR, "Polling failed: %s", curl_easy_strerror(res));

        if (strstr(response.ptr, "\"status\": \"done\"")) {
            char *start = strstr(response.ptr, "\"result\":");
            if (!start) elog(ERROR, "Missing result in response");
            start = strchr(start, '"');
            start = strchr(start + 1, '"');
            char *end = strchr(start + 1, '"');
            *end = '\0';
            curl_easy_cleanup(curl);
            return pstrdup(start + 1);
        }

        sleep(1);
    }

    curl_easy_cleanup(curl);
    elog(ERROR, "MAB task timed out after waiting");
    return NULL;
}

// Datum dbtune_mab_tune(PG_FUNCTION_ARGS) {
//     if (!enable_dbtune_mab)
//         ereport(ERROR, (errmsg("DBTune MAB is disabled.")));

//     text *table = PG_GETARG_TEXT_P(0);
//     ArrayType *columns = PG_GETARG_ARRAYTYPE_P(1);
//     char *table_cstr = text_to_cstring(table);

//     Datum *elems;
//     int nelems;
//     deconstruct_array(columns, TEXTOID, -1, false, 'i', &elems, NULL, &nelems);

//     StringInfo json = makeStringInfo();
//     appendStringInfo(json, "{\"table\": \"%s\", \"columns\": [", table_cstr);
//     for (int i = 0; i < nelems; i++) {
//         if (i > 0) appendStringInfoString(json, ", ");
//         appendStringInfo(json, "\"%s\"", TextDatumGetCString(elems[i]));
//     }
//     appendStringInfoString(json, "], \"options\": {}}");

//     char *task_id = send_post_and_get_id(json->data);
//     elog(NOTICE, "🎯 Submitted MAB task: %s", task_id);

//     char *result = poll_until_done(task_id);
//     elog(NOTICE, "✅ Result received");

//     PG_RETURN_TEXT_P(cstring_to_text(result));
// }

Datum dbtune_mab_tune(PG_FUNCTION_ARGS) {
    if (!dbtune_mab_tuning)
        ereport(ERROR, (errmsg("DBTune MAB is disabled. Enable with: SET dbtune.enable_mab = true;")));

    text *table;
    ArrayType *columns;
    char *table_cstr;
    Datum *elems;
    int nelems;
    int i;
    CURL *curl;
    struct curl_string response;
    CURLcode res;
    char *start, *end;

    table = PG_GETARG_TEXT_P(0);
    columns = PG_GETARG_ARRAYTYPE_P(1);
    table_cstr = text_to_cstring(table);

    deconstruct_array(columns, TEXTOID, -1, false, 'i', &elems, NULL, &nelems);

    StringInfo json = makeStringInfo();
    appendStringInfo(json, "{\"table\": \"%s\", \"columns\": [", table_cstr);
    for (i = 0; i < nelems; i++) {
        if (i > 0) appendStringInfoString(json, ", ");
        appendStringInfo(json, "\"%s\"", TextDatumGetCString(elems[i]));
    }
    appendStringInfoString(json, "], \"options\": {}}\n");

    elog(LOG, "[DBTune MAB] JSON payload: %s", json->data);

    curl = curl_easy_init();
    if (!curl)
        ereport(ERROR, (errmsg("[DBTune] Failed to init libcurl")));

    init_string(&response);

    struct curl_slist *headers = NULL;
    headers = curl_slist_append(headers, "Content-Type: application/json");
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);

    elog(LOG, "[DBTune] curl target URL: %s", mab_service_url);
    curl_easy_setopt(curl, CURLOPT_URL, mab_service_url);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, 5L);
    curl_easy_setopt(curl, CURLOPT_VERBOSE, 1L);
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, json->data);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, writefunc);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);

    res = curl_easy_perform(curl);
    elog(LOG, "[DBTune] curl_easy_perform result: %d", res);
    if (res != CURLE_OK)
        ereport(ERROR, (
            errmsg("curl_easy_perform() failed: %s", curl_easy_strerror(res)),
            errdetail("Request body was: %s. Response buffer: %s", json->data, response.ptr)
        ));

    curl_easy_cleanup(curl);

    start = strstr(response.ptr, "\"suggestion\":");
    if (!start)
        ereport(ERROR, (errmsg("MAB service did not return a suggestion"),
                        errdetail("Response was: %s", response.ptr)));

    start = strchr(start + 1, '"');
    start = strchr(start + 1, '"');
    end = strchr(start + 1, '"');
    *end = '\0';

    PG_RETURN_TEXT_P(cstring_to_text(start + 1));
}