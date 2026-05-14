FROM postgres:15

RUN apt-get update && apt-get install -y \
    build-essential curl libcurl4-openssl-dev \
    postgresql-server-dev-15

COPY dbtune_pg_mab_extension /plugin/dbtune_pg_mab_extension
COPY dbtune_pg_colse_extension /plugin/dbtune_pg_colse_extension

RUN make -C /plugin/dbtune_pg_mab_extension && make -C /plugin/dbtune_pg_mab_extension install
RUN make -C /plugin/dbtune_pg_colse_extension && make -C /plugin/dbtune_pg_colse_extension install

RUN echo "shared_preload_libraries = 'dbtune_mab,dbtune_colse'" >> /usr/share/postgresql/postgresql.conf.sample
