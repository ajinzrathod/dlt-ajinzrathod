"""Drop all Iceberg tables and purge data files from the catalog.

Run inside the dlt-loader container:
    python /app/reset.py

Or from the host:
    docker exec dlt-loader python /app/reset.py
"""

import os

from pyiceberg.catalog import load_catalog

catalog = load_catalog(
    "default",
    **{
        "type": "rest",
        "uri": os.environ.get("PYICEBERG_CATALOG__DEFAULT__URI", "http://iceberg-rest:8181"),
        "warehouse": os.environ.get(
            "PYICEBERG_CATALOG__DEFAULT__WAREHOUSE", "s3://warehouse"
        ),
        "s3.endpoint": os.environ.get(
            "PYICEBERG_CATALOG__DEFAULT__S3__ENDPOINT", "http://minio:9000"
        ),
        "s3.access-key-id": os.environ.get(
            "PYICEBERG_CATALOG__DEFAULT__S3__ACCESS_KEY_ID", "admin"
        ),
        "s3.secret-access-key": os.environ.get(
            "PYICEBERG_CATALOG__DEFAULT__S3__SECRET_ACCESS_KEY", "password"
        ),
        "s3.region": os.environ.get(
            "PYICEBERG_CATALOG__DEFAULT__S3__REGION", "us-east-1"
        ),
        "s3.path-style-access": "true",
    },
)

namespaces = catalog.list_namespaces()
if not namespaces:
    print("No namespaces found — catalog is already clean.")
    raise SystemExit(0)

for ns in namespaces:
    ns_name = ".".join(ns)
    tables = catalog.list_tables(ns)
    for table_id in tables:
        full_id = ".".join(table_id)
        print(f"Dropping table: {full_id}")
        catalog.drop_table(table_id)

    print(f"Dropping namespace: {ns_name}")
    try:
        catalog.drop_namespace(ns)
    except Exception as e:
        print(f"  Warning: could not drop namespace {ns_name}: {e}")

print("\nDone. All tables and snapshots purged.")
