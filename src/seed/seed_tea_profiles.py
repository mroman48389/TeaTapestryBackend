# One-time seeding from original CSV

import csv
from src.db.models.tea_profiles_model import TeaProfile

from src.utils.session_utils import get_session
from src.utils.csv_utils import parse_array, parse_numeric

# SQL Equivalent:
# INSERT INTO tea_profiles (name, tea_type, country_of_origin, avg_price_per_oz_usd)
# VALUES ('2007 Liming Golden Peacock Pu-erh', 'pu-erh', 'China', 2.25);

# new_tea = TeaProfile(
#     name="2007 Liming Golden Peacock Pu-erh",
#     tea_type="pu-erh",
#     country_of_origin="China",
#     subregions=["Yunnan", "Xishuangbanna Dai Autonomous Prefecture", "Menghai county"],
#     avg_price_per_oz_usd=2.25,
#     processing="wet-stored;raw pu-erh",
#     liquor_appearance=["golden orange", "warm light brown", "pale caramel"],
#     liquor_aroma=["strongly floral", "peppery", "cantaloupe", "sweet"],
#     liquor_taste=["pungent", "sweet", "thick", "creamy"],
#     liquor_body_mouthfeel=["medium-heavy body", "tingling", "juicy", "smooth"],
#     dry_leaf_aroma=["peppery", "bright", "fiery", "woody"],
#     wet_leaf_appearance=["olive green", "brown", "red"],
#     wet_leaf_aroma=["spicy", "black pepper", "sour cherry", "tobacco"]
# )
# session.add(new_tea)

# To create the database (one time before running the code below), do the following in PowerShell,
#
# First, connect to psql using your username. If username has special 
# characters, use those instead of what you entered in the env file)
#   
#     psql -U [username] -h localhost 
#   
# Then create the database:
#       
#     CREATE DATABASE tea_profiles;
#
# Use \l to list all dtabases and confirm it was created. Then quit/exit psql:
#   
#     psql \q 

def seed_tea_profiles():

    with get_session() as session:
        # If there are no rows in the database, seed it. query(TeaProfile)
        # grabs the tea_profiles table, using the TeaProfile model to define
        # its structure. 
        # 
        # SQL: SELECT COUNT(*) FROM tea_profiles;
        if session.query(TeaProfile).count() == 0:
            print("test 2")
            # with is a context manager. Behind the scenes, it's doing the
            # following: 
            #
            #   csvfile = open('data/seeds/tea_profiles_2025-11-12.csv', newline = '').__enter__()
            #   try:
            #       # do stuff
            #   finally:
            #       open('data/seeds/tea_profiles_2025-11-12.csv', newline = '').__exit__()
            #
            with open('data/seeds/tea_profiles_2025-11-12.csv', newline = '') as csvfile:
                reader = csv.DictReader(csvfile)

                for row in reader:
                    tea_profile = TeaProfile(
                        name = row['name'],
                        alternative_names = parse_array(row['alternative_names']),
                        tea_type = row['tea_type'],
                        cultivars = parse_array(row['cultivars']),
                        processing = row['processing'],
                        oxidation_level = row['oxidation_level'],
                        cultural_significance = row['cultural_significance'],
                        cultural_significance_source = row['cultural_significance_source'],

                        country_of_origin = row['country_of_origin'],
                        subregions = parse_array(row['subregions']),
                        avg_price_per_oz_usd = parse_numeric(row['avg_price_per_oz_usd']),

                        liquor_appearance = parse_array(row['liquor_appearance']),
                        liquor_aroma = parse_array(row['liquor_aroma']),
                        liquor_taste = parse_array(row['liquor_taste']),
                        liquor_body_mouthfeel = parse_array(row['liquor_body_mouthfeel']),
                        body_effect = parse_array(row['body_effect']),

                        dry_leaf_appearance = parse_array(row['dry_leaf_appearance']),
                        dry_leaf_aroma = parse_array(row['dry_leaf_aroma']),

                        wet_leaf_appearance = parse_array(row['wet_leaf_appearance']),
                        wet_leaf_aroma = parse_array(row['wet_leaf_aroma']),
                    )
                    session.add(tea_profile)

            session.commit()

# SQL
#
# COPY tea_profiles (
#     name,
#     alternative_names,
#     tea_type,
#     cultivars,
#     processing,
#     oxidation_level,
#     cultural_significance,
#     cultural_significance_source,
#     country_of_origin,
#     subregions,
#     avg_price_per_oz_usd,
#     liquor_appearance,
#     liquor_aroma,
#     liquor_taste,
#     liquor_body_mouthfeel,
#     body_effect,
#     dry_leaf_appearance,
#     dry_leaf_aroma,
#     wet_leaf_appearance,
#     wet_leaf_aroma
# )
# FROM '/data/tea_profiles.csv'
# WITH (FORMAT csv, HEADER true);
