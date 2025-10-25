"""Constants and configurations for the project"""

import duckdb

# define the path to the parquet file
p_trj_2021nov = "~/100_database/_mobile/2021Nov_trj_oa.parquet"

# Connect to DuckDB
conn_duck = duckdb.connect("data/duckdb/temp.db")

# read the parquet file to duckdb
conn_duck.execute(
    f"CREATE TABLE IF NOT EXISTS trj_2021nov AS SELECT * FROM parquet_scan('{p_trj_2021nov}')"
)
