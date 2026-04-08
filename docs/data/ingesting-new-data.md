
# How to Ingest New Data
>
>    1. Create a new csv file, using the latest one from data/backups as a template.
>    2. Copy the new csv file into data/ingestion and data/backups. 
>    3. Update the ingestion runner in src/app (such as ingest_tea_profiles.py) to point to the new csv file you wish to ingest.
>    4. Run the ingest script, such as scripts/ingest_tea_profiles.ps1.
>    5. You can run the scripts/connect_postgres.ps1 script and then do something like "SELECT COUNT(*) FROM tea_profiles;" as an extra check 
>       to make sure the data was added successfully.