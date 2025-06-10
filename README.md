# dbtune



## Project Structure

AIDB/
├── dbtune_mab_service/               # Python-based MAB tuning microservice
│   ├── bandits/                      # Multi-armed bandit algorithms (e.g., C3UCB, Thompson Sampling)
│   ├── configs/                      # Configuration files for workloads and experiments
│   ├── db_tools/                     # PostgreSQL wrappers and tuning utilities
│   ├── hyp_files/                    # Hypothetical index metadata
│   ├── logs/                         # Logging outputs
│   ├── notebooks/                    # (Optional) Jupyter notebooks for analysis
│   ├── resource/                     # Static resources
│   ├── shared/                       # Shared classes/utilities across modules
│   ├── test_inputs/                 # Query input samples for testing
│   ├── tests/                        # Pytest test suite
│   ├── workloads/                    # Workload SQL definitions
│   ├── app.py                        # FastAPI app entrypoint
│   ├── celery_worker.py              # Celery worker for async execution
│   ├── constants.py, schemas.py      # Core data structures and constants
│   └── requirements.txt              # Python dependencies
│
├── dbtune_pg_mab_extension/         # PostgreSQL C extension for MAB
│   ├── dbtune_mab--0.0.1.sql         # SQL installation script
│   ├── dbtune_mab.c                  # C source for custom PG function
│   ├── dbtune_mab.control            # PG extension control file
│   ├── Makefile, Dockerfile          # Build tools for PG extension
│   └── logs/, hyp_files/             # Extension logs and metadata
│
├── hyp_files/                        # Global hypothetical index records
├── logs/                             # Top-level logs (optional)
├── docker-compose.yml                # Docker orchestration file


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