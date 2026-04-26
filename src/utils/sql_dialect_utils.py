
def get_sql_from_dialect(session, postgres_sql: str, sqlite_sql: str) -> str:
    # bind should never be None. Assert to make Pylance happy.
    bind = session.bind
    assert bind is not None  
    dialect = bind.dialect.name

    if dialect == "postgresql":
        return postgres_sql
    
    elif dialect == "sqlite":
        return sqlite_sql
    
    else:
        raise NotImplementedError(f"Dialect {dialect} not supported.")