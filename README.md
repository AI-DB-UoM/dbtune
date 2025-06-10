

## Setup Instructions

### Docker Commands

```bash
# Stop all containers and remove volumes/networks
docker compose down --volumes --remove-orphans

# Rebuild everything from scratch
docker compose up --build

# Or just start containers (no rebuild)
docker compose up
```

### Generate Benchmark Data

> (You should add instructions here if you're using dsdgen or other scripts.)

For example:
```bash
cd /path/to/tpcds-kit/tools
./dsdgen -scale 1 -dir /data/tpcds_data
```

### Import Data & Run Queries

> (Specify your import method: COPY, psql, or Python scripts.)

### Install Database Extensions

```bash
apt update && apt install -y git make gcc postgresql-server-dev-15

cd /tmp
git clone https://github.com/HypoPG/hypopg.git
cd hypopg
make && make install

apt remove -y git make gcc postgresql-server-dev-15
apt autoremove -y && apt clean
rm -rf /tmp/hypopg
```

### Enable Extensions in PostgreSQL

```bash
-- Run inside PostgreSQL to activate the extension
CREATE EXTENSION hypopg;
-- If needed (for custom extensions)
CREATE FUNCTION dbtune_mab_tune(text, text[]) RETURNS text
AS 'dbtune_mab', 'dbtune_mab_tune'
LANGUAGE C STRICT;
```