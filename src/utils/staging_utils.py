def get_staging_table_name(base_table_name: str) -> str:
    return f"staging.{base_table_name}_staging"
