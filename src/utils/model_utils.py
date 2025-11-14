def get_model_column_names(model, include_primary_key: bool=True) -> list[str]:    
    return [col.name for col in model.__table__.columns if (not col.primary_key) or include_primary_key]

def get_model_column_names_as_str(model, include_primary_key: bool=True) -> str:    
    return ", ".join(get_model_column_names(model, include_primary_key))