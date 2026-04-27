import logging

from src.utils.session_utils import get_session_cm
from src.ingest.ingest import ingest_data
from src.db.models.tea_profiles_model import (
    TeaProfileModel, TeaProfileModelFields, REQUIRED_TEA_PROFILE_MODEL_FIELDS
)

# use __name__ to get a logger named after the module we're in.
logger = logging.getLogger(__name__)

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
            ingest_data(
                session,
                "data/ingestion/tea_profiles_ingestion_testing.csv",
                TeaProfileModel,
                [
                    field for field in REQUIRED_TEA_PROFILE_MODEL_FIELDS 
                    if field != TeaProfileModelFields.ID
                ],
                [TeaProfileModelFields.NAME]
            )
        logger.info("tea_profiles ingestion complete.")
        
    except Exception:
        logger.exception("Ingestion failed.")
        raise