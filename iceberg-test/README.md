# Iceberg Streaming Test Harness

Local Docker-based test environment to verify that dlt Iceberg writes
(append, replace, upsert) stream data with **constant memory** and produce
**minimal Iceberg snapshots**.

## Architecture

```
┌────────────────────┐
│  Your Mac           │
│  generate.py        │──→ parquet_output/   (initial data)
│  generate_updates.py│──→ parquet_updates/  (upsert data)
└────────┬───────────┘
         │ mounted as volumes
         ▼
┌────────────────────────────────────────────┐
│  Docker Compose                            │
│  ┌──────────┐  ┌─────────────┐  ┌───────┐ │
│  │ dlt-loader│  │ iceberg-rest│  │ MinIO │ │
│  │ (Python)  │  │ (catalog)   │  │ (S3)  │ │
│  └──────────┘  └─────────────┘  └───────┘ │
│      4GB mem        :8181          :9000   │
│      limit                         :9001  │
└────────────────────────────────────────────┘
```

- **MinIO** — S3-compatible object store holding Iceberg data files
- **iceberg-rest** — Iceberg REST catalog backed by MinIO
- **dlt-loader** — Python container with dlt installed; your local
  `dlt/` source code is mounted in so changes are reflected instantly

## Prerequisites

- Docker & Docker Compose
- `uv` (for local Python scripts)

## Quick Start

### 1. Generate test data (on your Mac)

```bash
cd iceberg-test

# Install project deps (only needed once)
cd .. && make dev && cd iceberg-test

# Generate initial parquet files (1.8M rows, 400 columns)
uv run python generate.py

# Generate update parquet files (1,500 rows from 3 original files)
uv run python generate_updates.py
```

### 2. Start Docker services

```bash
cd iceberg-test
docker compose up --build -d
```

This starts MinIO, the Iceberg REST catalog, and the dlt-loader container
(4GB memory limit).

### 3. Verify services are running

```bash
docker compose ps
```

You should see `dlt-minio`, `dlt-iceberg-rest`, and `dlt-loader` all running.
MinIO console is available at http://localhost:9001 (admin/password).

## Test Workflows

All test scripts run **inside** the dlt-loader container because they need
access to MinIO and the Iceberg REST catalog via Docker networking.

### Test: Replace (initial load)

```bash
docker exec dlt-loader python /app/test-large-parquet-docker.py
```

Loads all parquet files from `parquet_output/` with `write_disposition="replace"`.
Streams data batch-by-batch — memory should stay constant even with large datasets.

### Test: Upsert

```bash
docker exec dlt-loader python /app/test-upsert-docker.py
```

Loads update files from `parquet_updates/` with `write_disposition="merge"`
and `primary_key="id"`. Updates existing rows that match, inserts new ones.

### Test: Append

Edit `test-large-parquet-docker.py` and change `write_disposition="replace"`
to `write_disposition="append"`, then run it again. Rows are added without
deduplication.

## Inspection & Maintenance

### Check Iceberg snapshots

```bash
docker exec dlt-loader python /app/check-snapshots.py
```

Shows snapshot count, operations (APPEND/OVERWRITE/DELETE), row counts,
and file counts for each snapshot.

### Reset (drop all tables)

```bash
docker exec dlt-loader python /app/reset.py
```

Drops all Iceberg tables and namespaces from the catalog. Does not
restart containers or delete MinIO volumes.

### Full reset (nuke everything)

```bash
cd iceberg-test
docker compose down -v
docker compose up --build -d
```

Removes all containers **and** volumes (MinIO data wiped).

### Browse MinIO

Open http://localhost:9001 in your browser.
- Username: `admin`
- Password: `password`
- Bucket: `warehouse`

## What to Look For

### Memory

The test scripts log RSS and Arrow buffer usage. With streaming enabled:
- RSS should stay **well below** the 4GB container limit
- Arrow allocated bytes should not grow unbounded

### Snapshots

After a **replace** load, `check-snapshots.py` should show:
- 1 DELETE snapshot (clearing old data)
- 1 APPEND snapshot (adding all new data files)

After an **upsert**, you should see:
- 1 OVERWRITE snapshot (updated rows — rewrites affected data files)
- 1 APPEND snapshot (insert portion via `add_files`)
- Total row count should remain the same if all rows were updates

### Key invariants

- No `.to_table()` on the full dataset — data streams batch-by-batch
- Only one RecordBatch + one temp parquet file in memory at a time
- All file registrations happen in a single atomic Iceberg transaction

## File Reference

| File | Runs on | Purpose |
|------|---------|---------|
| `generate.py` | Mac | Create initial parquet files in `parquet_output/` |
| `generate_updates.py` | Mac | Create upsert parquet files in `parquet_updates/` |
| `test-large-parquet-docker.py` | Docker | Run dlt pipeline (replace/append) |
| `test-upsert-docker.py` | Docker | Run dlt pipeline (merge/upsert) |
| `check-snapshots.py` | Docker | Inspect Iceberg table snapshots |
| `reset.py` | Docker | Drop all tables from catalog |
| `docker-compose.yml` | — | Service definitions |
| `Dockerfile.loader` | — | Container image for dlt-loader |
