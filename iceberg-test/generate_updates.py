"""Generate update parquet files that touch rows spread across 2-3 original files.

Reads the original parquet_output/ to discover which IDs exist in which files,
then picks a sample from 3 different files and writes them with new random data
into parquet_updates/.

Run from iceberg-test/:
    uv run python generate_updates.py
"""

import os
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

ORIGINAL_DIR = Path("./parquet_output")
UPDATE_DIR = Path("./parquet_updates")
ROWS_PER_FILE = 500  # how many rows to update per source file
NUM_SOURCE_FILES = 3  # pick rows from this many original files
STR_LEN = 12


def fast_string_array(n: int) -> pa.Array:
    raw = np.random.bytes(n * 6)
    arr = raw.hex()
    data = [arr[i : i + STR_LEN] for i in range(0, len(arr), STR_LEN)]
    return pa.array(data[:n])


def main():
    original_files = sorted(ORIGINAL_DIR.glob("*.parquet"))
    if not original_files:
        print(f"No parquet files found in {ORIGINAL_DIR}")
        return

    schema = pq.read_schema(original_files[0])
    non_id_cols = [f.name for f in schema if f.name != "id"]

    n_files = len(original_files)
    # pick files spread across the range: first, middle, last
    indices = [0, n_files // 2, n_files - 1][:NUM_SOURCE_FILES]
    picked_files = [original_files[i] for i in indices if i < n_files]

    UPDATE_DIR.mkdir(parents=True, exist_ok=True)

    total_rows = 0
    for out_idx, pf_path in enumerate(picked_files):
        pf = pq.ParquetFile(str(pf_path))
        # read just enough rows to get our sample IDs
        first_batch = next(pf.iter_batches(batch_size=ROWS_PER_FILE, columns=["id"]))
        ids = first_batch.column("id")

        n = len(ids)
        columns = [ids]
        for col_name in non_id_cols:
            columns.append(fast_string_array(n))

        update_table = pa.Table.from_arrays(columns, schema=schema)
        out_path = UPDATE_DIR / f"update_{out_idx}.parquet"
        pq.write_table(update_table, out_path, compression="snappy")
        total_rows += n
        print(
            f"  [{out_idx + 1}/{len(picked_files)}] Picked {n} IDs from {pf_path.name}"
            f" → {out_path.name}"
        )

    print(
        f"\nDone. Generated {len(picked_files)} update files"
        f" ({total_rows:,} rows total) in {UPDATE_DIR}"
    )


if __name__ == "__main__":
    main()
