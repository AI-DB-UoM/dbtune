FROM postgres:15

RUN apt-get update && apt-get install -y \
    build-essential curl libcurl4-openssl-dev \
    postgresql-server-dev-15

COPY . /plugin
WORKDIR /plugin

RUN make && make install

# Enable extension-related defaults
RUN echo "shared_preload_libraries = 'dbtune_mab'" >> /usr/share/postgresql/postgresql.conf.sample
RUN echo "dbtune.enable_mab = on" >> /usr/share/postgresql/postgresql.conf.sample
