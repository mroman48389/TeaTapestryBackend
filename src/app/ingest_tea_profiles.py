import glob

from src.utils.log_utils import safe_debug, safe_exception
from src.utils.session_utils import get_session_cm
from src.ingest.pipeline_orchestrator import ingest_data
from src.db.models.tea_profiles_model import (
    TeaProfileModel, TeaProfileModelFields, REQUIRED_TEA_PROFILE_MODEL_FIELDS
)

# Only run this block if the file is executed directly as the main
# program and not if the file is imported. 
# 
# Every Python file has a __name__ dunder variable. 
# When you run a file directly, this gets set to __main__ and
# when the file is imported as a module, __name__ is set to
# the file name.
if __name__ == "__main__":
    try:
        with get_session_cm() as session:
            for csv_path in glob.glob("data/ingestion/batch/*.csv"):
                ingest_data(
                    session,
                    csv_path,
                    TeaProfileModel,
                    [
                        field for field in REQUIRED_TEA_PROFILE_MODEL_FIELDS 
                        if field != TeaProfileModelFields.ID
                    ],
                    [TeaProfileModelFields.NAME]
                )
                safe_debug(f"Ingested {csv_path}")
                
        safe_debug("tea_profiles ingestion complete.")
        
    except Exception:
        safe_exception("Ingestion failed.")
        raise