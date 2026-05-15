
psql -d imdbload -h /var/run/postgresql -U guanlil1


\d company_type
\d info_type
\d movie_companies
\d movie_info_idx
\d title

\timing on

SELECT
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND (
        indexname LIKE 'ixn\_%' ESCAPE '\'   -- ixn_*
        OR indexname LIKE 'ix%'              -- ix* (including ixn_*)
        OR indexname LIKE 'mv\_%' ESCAPE '\' -- mv_*
      )
ORDER BY tablename, indexname;



-- 1) movie_companies(company_type_id, movie_id)
SELECT * 
FROM hypopg_create_index(
  'CREATE INDEX ON public.movie_companies USING btree (company_type_id, movie_id);'
);

-- 2) movie_info_idx(info_type_id, movie_id)
SELECT * 
FROM hypopg_create_index(
  'CREATE INDEX ON public.movie_info_idx USING btree (info_type_id, movie_id);'
);

-- 3) Create a trigram index for mc.note (planner-level only)
SELECT * 
FROM hypopg_create_index(
  'CREATE INDEX ON public.movie_companies USING gin (note gin_trgm_ops);'
);


EXPLAIN (BUFFERS, FORMAT TEXT)
SELECT MIN(mc.note) AS production_note,
       MIN(t.title) AS movie_title,
       MIN(t.production_year) AS movie_year
FROM company_type AS ct,
     info_type AS it,
     movie_companies AS mc,
     movie_info_idx AS mi_idx,
     title AS t
WHERE ct.kind = 'production companies'
  AND it.info = 'top 250 rank'
  AND mc.note NOT LIKE '%(as Metro-Goldwyn-Mayer Pictures)%'
  AND (mc.note LIKE '%(co-production)%'
       OR mc.note LIKE '%(presents)%')
  AND ct.id = mc.company_type_id
  AND t.id = mc.movie_id
  AND t.id = mi_idx.movie_id
  AND mc.movie_id = mi_idx.movie_id
  AND it.id = mi_idx.info_type_id;
