# Layer 2 (Domain/service/middle layer): Contains services for all health / smoke tests.

from src.db.repositories.health.db_tea_profiles_repository import HealthDBTeaProfilesRepository

class HealthService:
    def __init__(self):
        self.db_tea_profiles_repo = HealthDBTeaProfilesRepository()

    def check_all_connections(self) -> dict:
        # Call this to check that all resources can connect. 
        return {
            "db_tea_profiles": self.db_tea_profiles_repo.check_connection()
        }