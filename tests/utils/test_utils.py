from fastapi.routing import APIRoute

from src.utils.session_utils import get_session_cm
from src.db.models.tea_profiles_model import TeaProfileModel

def get_dummy_value_for_param_type(param_type):
    """Return a dummy value based on the parameter type."""
    if param_type is int:
        return "1"
    elif param_type is float:
        return "1.0"
    elif param_type.__name__ == "UUID":
        return "123e4567-e89b-12d3-a456-426614174000"
    # Default to string for anything else
    else:
        return "test"

def get_path_with_dummy_params(route: APIRoute) -> str:
    """
        Replace dynamic parameters in the route path, if they exist, with 
        type-appropriate dummy values.
    """
    path = route.path
    for param in route.dependant.path_params:
        val = get_dummy_value_for_param_type(param.type_)
        path = path.replace(f"{{{param.name}}}", val)
    return path

def get_id_from_tea_name(name: str) -> int:
    with get_session_cm() as session:
        obj = session.query(TeaProfileModel).filter_by(name = name).first()
        if not obj:
            raise ValueError(f"No tea profile found with name = {name}")
        return obj.id