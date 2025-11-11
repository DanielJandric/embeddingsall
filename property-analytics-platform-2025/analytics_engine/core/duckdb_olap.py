import duckdb

def get_connection(cache_dir: str = "/tmp/duckdb_cache"):
    con = duckdb.connect()
    con.execute("SET enable_http_file_cache = true")
    con.execute(f"SET http_file_cache_dir = '{cache_dir}'")
    return con


