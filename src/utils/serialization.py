def to_serializable(data):
    # Pydantic models
    if hasattr(data, "model_dump"):
        return data.model_dump()

    # SQLAlchemy model
    if hasattr(data, "__table__"):
        return {
            column.name: getattr(data, column.name)
            for column in data.__table__.columns
        }

    # List of items
    if isinstance(data, list):
        return [to_serializable(item) for item in data]

    # Already serializable (dict, str, int, etc.)
    return data
