import os
from pathlib import Path
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from tqdm import tqdm


# --------------------------------
# CONFIG
# --------------------------------
OUTPUT_DIR = Path("./parquet_output")
# NUM_ROWS = 10_000_000        # total rows
NUM_ROWS = 11_000_00        # total rows

NUM_COLS = 400              # number of columns
BATCH_SIZE = 100_000        # rows per file (tune for speed)
STR_LEN = 12                # length of dummy strings


def create_schema(num_cols: int) -> pa.Schema:
    """Arrow schema: `id` (PK) + string columns."""
    fields = [pa.field("id", pa.string())]
    fields += [pa.field(f"col_{i}", pa.string()) for i in range(1, num_cols)]
    return pa.schema(fields)


def fast_string_array(n: int) -> pa.Array:
    """Vectorized generation of n random strings, extremely fast."""
    # Random bytes converted to hex → super fast
    raw = np.random.bytes(n * 6)  # 6 bytes → 12 hex chars
    arr = raw.hex()
    # Split hex string into chunks of STR_LEN
    data = [arr[i:i + STR_LEN] for i in range(0, len(arr), STR_LEN)]
    return pa.array(data[:n])


def generate_batch(schema: pa.Schema, batch_size: int, start_id: int) -> pa.RecordBatch:
    """Generate a record batch: `id` column as PK + random string columns."""
    id_array = pa.array([str(i) for i in range(start_id, start_id + batch_size)])
    other_cols = [fast_string_array(batch_size) for _ in schema.names[1:]]
    cols = [id_array] + other_cols
    return pa.RecordBatch.from_arrays(cols, schema=schema)


def write_parquet_files():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    schema = create_schema(NUM_COLS)

    rows_left = NUM_ROWS
    global_row_id = 0
    file_idx = 0

    print(f"Generating {NUM_ROWS:,} rows into Parquet files (fast mode)...")

    with tqdm(total=NUM_ROWS, unit="rows") as pbar:
        while rows_left > 0:
            bs = min(BATCH_SIZE, rows_left)
            batch = generate_batch(schema, bs, global_row_id)
            table = pa.Table.from_batches([batch])

            file_path = OUTPUT_DIR / f"part_{file_idx}.parquet"
            pq.write_table(table, file_path, compression="snappy")

            rows_left -= bs
            global_row_id += bs
            file_idx += 1
            pbar.update(bs)

    print(f"\n✔ Done. Generated {file_idx} Parquet files at {OUTPUT_DIR}")


if __name__ == "__main__":
    write_parquet_files()
