"""Check Iceberg table snapshot count and details."""

import os

from pyiceberg.catalog import load_catalog

catalog = load_catalog(
    "default",
    **{
        "type": "rest",
        "uri": os.environ.get("PYICEBERG_CATALOG__DEFAULT__URI", "http://iceberg-rest:8181"),
        "warehouse": os.environ.get("PYICEBERG_CATALOG__DEFAULT__WAREHOUSE", "s3://warehouse"),
        "s3.endpoint": os.environ.get("PYICEBERG_CATALOG__DEFAULT__S3__ENDPOINT", "http://minio:9000"),
        "s3.access-key-id": os.environ.get("PYICEBERG_CATALOG__DEFAULT__S3__ACCESS_KEY_ID", "admin"),
        "s3.secret-access-key": os.environ.get("PYICEBERG_CATALOG__DEFAULT__S3__SECRET_ACCESS_KEY", "password"),
        "s3.region": os.environ.get("PYICEBERG_CATALOG__DEFAULT__S3__REGION", "us-east-1"),
        "s3.path-style-access": "true",
    },
)

TABLE_ID = os.environ.get("TABLE_ID", "large_test.wide_table")

try:
    table = catalog.load_table(TABLE_ID)
except Exception as e:
    print(f"Could not load table '{TABLE_ID}': {e}")
    print(f"\nAvailable namespaces: {catalog.list_namespaces()}")
    raise SystemExit(1)

snapshots = table.metadata.snapshots
print(f"\nTable: {TABLE_ID}")
print(f"Location: {table.location()}")
print(f"Snapshot count: {len(snapshots)}")

for i, snap in enumerate(snapshots):
    summary = snap.summary
    print(
        f"\n  [{i + 1}] snapshot_id={snap.snapshot_id}"
        f"\n      operation:    {summary.operation}"
        f"\n      added-files:  {summary.get('added-data-files', '?')}"
        f"\n      added-rows:   {summary.get('added-records', '?')}"
        f"\n      total-files:  {summary.get('total-data-files', '?')}"
        f"\n      total-rows:   {summary.get('total-records', '?')}"
    )
