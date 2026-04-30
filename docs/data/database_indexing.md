# Database Indexing 

> Tea profiles are read and filter-heavy. Users are likely to search by tea type, oxidation level, 
> country of origin, and liquor taste the most. To get fast, scalable queries, we added a set of
> PostgreSQL indexes. This prevents PostgreSQL from needing to scan the entire tea_profiles
> database, instead jumping directly to matching rows.

## 1. Index Types Used

>    1. B-tree Indexes: The default index type, good for equality and range filtering and sorting. 
>       Used on scalar fields like tea_type, oxidation_level, country_of_origin.
>
>    2. GIN (Generalized Inverted Index): Good for arrays, JSONB, and full-text searches. Used on liquor_taste.

## 2. Indexes Added

> In pgAdmin, we went to to Servers --> PostgreSQL 18 --> Databases --> tea_profiles --> right-click --> Query Tool
> and ran the following queries to add the indexes. You can see them under tea_profiles --> Schemas --> 
> Tables --> tea_profiles --> Indexes.

>    1. B-tree Indexes:
>       
>       CREATE INDEX idx_tea_type 
>       ON tea_profiles (tea_type);
>
>       CREATE INDEX idx_oxidation_level 
>       ON tea_profiles (oxidation_level);
>
>       CREATE INDEX idx_country_of_origin 
>       ON tea_profiles (country_of_origin);
>
>    2. Composite B-tree Indexes: These are highly likely to be paired in filtering.
>
>       CREATE INDEX idx_country_oxidation 
>       ON tea_profiles (country_of_origin, oxidation_level);
>
>       CREATE INDEX idx_country_teatype 
>       ON tea_profiles (country_of_origin, tea_type);
>
>   3. GIN Index
>
>      CREATE INDEX idx_liquor_taste_gin 
>      ON tea_profiles USING GIN (liquor_taste);


