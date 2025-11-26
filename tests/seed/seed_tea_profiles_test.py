from src.db.models.tea_profiles_model import TeaProfile
from src.app.seed_tea_profiles import seed_tea_profiles
from src.utils.sample_data_utils import get_sample_tea_profiles_data

# Note that create_test_db is scoped to function, so 
# the same db object will get used each time.
def test_seed_tea_profiles(create_test_db, create_test_csv):
    csv_file = create_test_csv(TeaProfile, get_sample_tea_profiles_data())
    seed_tea_profiles(create_test_db, csv_file)
    result = create_test_db.query(TeaProfile).all()
    assert len(result) > 0