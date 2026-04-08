SELECT *
FROM tea_profiles
WHERE EXISTS (
    SELECT 1
    FROM unnest(liquor_taste) AS t(note)
    WHERE note ILIKE '%spinach%'
);
