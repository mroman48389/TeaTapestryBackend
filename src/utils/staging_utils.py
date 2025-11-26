def get_staging_table_name(session, base_table_name: str) -> str:
    dialect = session.bind.dialect.name

    if dialect == "postgresql":
        return f"staging.{base_table_name}_staging"
    
    # SQLite doesn't support scehemas like staging.
    elif dialect == "sqlite":
        return f"{base_table_name}_staging"
    
    else:
        raise NotImplementedError(f"Dialect {dialect} not supported.")
