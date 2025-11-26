from src.utils.session_utils import get_session
from src.ingest.ingest import ingest_data
from src.db.models.tea_profiles_model import (
    TeaProfile, TeaProfileFields, REQUIRED_TEA_PROFILE_FIELDS
)

# Only run this block if the file is executed directly as the main
# program and not if the file is imported. 
# 
# Every Python file has a __name__ dunder variable. 
# When you run a file directly, this gets set to __main__ and
# when the file is imported as a module, __name__ is set to
# the file name.
if __name__ == "__main__":
    with get_session() as session:
        ingest_data(
            session,
            "data/ingestion/tea_profiles_2025-11-17.csv",
            TeaProfile,
            [field for field in REQUIRED_TEA_PROFILE_FIELDS if field != TeaProfileFields.ID],
            ["name"]
        )
    print("tea_profiles ingestion complete")