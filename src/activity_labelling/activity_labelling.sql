

CREATE TABLE SAs_test (
    userid String,
    label Int32,
    start_time DateTime,
    end_time DateTime,
    n_pnts Float64,
    n_days Float64,
    o_lat Float64,
    o_lon Float64,
    d_lat Float64,
    d_lon Float64,
    o_label String,
    d_label String,
    distance Float64,
    activity_duration Float64,
    activity_type String,
    home_activity FixedString(1),
    work_activity FixedString(1),
    o_h9 String,
    d_h9 String,
    o_oa String,
    d_oa String
) ENGINE = MergeTree()
ORDER BY
    (userid, start_time);

INSERT INTO
    SAs_test
SELECT
    *
FROM
    file(
        '/var/lib/clickhouse/user_files/london_poi/2021Oct_trj_oa.parquet',
        'Parquet'
    );

CREATE TABLE IF NOT EXISTS poi_uk (
    ref_no Int64,
    name String,
    pointx_class Int64,
    feature_easting Float64,
    feature_northing Float64,
    pos_accuracy Int32,
    uprn Int64,
    topo_toid String,
    topo_toid_version Int32,
    usrn Int64,
    usrn_mi Int64,
    distance Float64,
    address_detail String,
    street_name String,
    locality String,
    geographic_county String,
    postcode String,
    verified_address String,
    admin_boundary String,
    telephone_number String,
    url String,
    brand String,
    qualifier_type String,
    qualifier_data String,
    provenance String,
    supply_date Date,
    longitude Float64,
    latitude Float64,
    hex_id String
) ENGINE = MergeTree()
ORDER BY
    (pointx_class);

INSERT INTO
    poi_uk
SELECT
    *
FROM
    file(
        '/var/lib/clickhouse/user_files/london_poi/poi202312.parquet',
        'Parquet'
    );

--feature_easting  min 131973 max 655511
--feature_northing min 11457 max 601169
-- CREATE TABLE IF NOT EXISTS pointx_class (
--     class_code Int64,
--     group Int64,
--     category Int64,
--     class Int64,
--     group_des String,
--     category_des String,
--     class_des String
-- ) ENGINE = MergeTree()
-- ORDER BY
--     (class_code);

-- INSERT INTO
--     pointx_class
-- SELECT *
-- FROM
--     file(
--         '/var/lib/clickhouse/user_files/london_poi/POI_CLSSIFICATION.csv',
--         'CSVWithNames'
--     );

CREATE TABLE IF NOT EXISTS pointx_class_with_degree (
    pointxclassificationcode Int64,
    groupdescription String,
    categorydescription String,
    classdescription String,
    firstdegreelabel String
) ENGINE = MergeTree()
ORDER BY
    (pointxclassificationcode);

INSERT INTO
    pointx_class_with_degree
SELECT *
FROM
    file(
        '/var/lib/clickhouse/user_files/london_poi/pointx_poi_v3_test.csv',
        'CSVWithNames'
    );

ALTER TABLE pointx_class_with_degree
UPDATE firstdegreelabel = replaceAll(lower(firstdegreelabel), ' ', '')
WHERE firstdegreelabel IS NOT NULL;

-- cp   /mnt/database/source_data/london_poi/pointx_poi_v3_test.csv  /mnt/database/Mobile-App-Data/data/labeling_test/pointx_poi_v3_test.csv

--------------------------------
CREATE TABLE IF NOT EXISTS temporal_activity_types_closest_test (
    tm_start_time String,
    tm_end_time String,
    education Float64,
    eatinganddrinking Float64,
    shopping_1 Float64,
    shopping_2 Float64,
    entertainment Float64,
    transport_activities Float64,
    others Float64
) ENGINE = MergeTree()
ORDER BY
    (tm_start_time);

INSERT INTO
    temporal_activity_types_closest_test
SELECT
    *
FROM
    file(
        '/var/lib/clickhouse/user_files/london_poi/temporal_activity_types_closest.csv',
        'CSVWithNames'
    );

-- activity weights

-- others, education, eatinganddrinking, shopping_1, shopping_2, entertainment, transport_activities
CREATE TABLE IF NOT EXISTS activity_weights (
    start_time String,
    activity_type String,
    type_weight Float64
) ENGINE = MergeTree()
ORDER BY
    (start_time);

INSERT INTO
    activity_weights (start_time, activity_type, type_weight)
SELECT
    start_time,
    group,
    weight
FROM
    file('/var/lib/clickhouse/user_files/london_poi/activity_weights.parquet', 'Parquet');

-- user filter
SELECT
    userid,
    label,
    start_time,
    end_time,
    o_lat,
    o_lon,
    activity_duration,
    home_activity,
    work_activity,
    o_h9
FROM
    SAs_test
where
    activity_type = 'STATIONARY'
    and home_activity = 'N'
    and work_activity = 'N'
    and firstdegreelabel IS not null;

SELECT
    ref_no,
    name,
    pointx_class,
    latitude,
    longitude,
    hex_id,
    class,
    group
FROM
    poi_uk
    left join pointx_class on poi_uk.pointx_class = pointx_class.class_code;

--------------------------------
-- label_hexring
--------------------------------
DROP TABLE IF EXISTS label_hexring;
CREATE TABLE IF NOT EXISTS label_hexring ENGINE = MergeTree()
ORDER BY (o_label) AS
With filtered_sas AS (
    -- Step 2: Filter SAs_test data and prepare its H3 ID.
    SELECT DISTINCT o_label, o_lat, o_lon, stringToH3(o_h9) AS o_h9_uint64
    FROM
        SAs_test
    WHERE
        activity_type = 'STATIONARY'
        AND home_activity = 'N'
        AND work_activity = 'N'
)
SELECT
    o_label,
    o_lat,
    o_lon,
    o_h9_uint64,
    arrayJoin(h3kRing(o_h9_uint64, 1)) AS k_ring_hex_id
FROM
    filtered_sas;

--------------------------------
-- poi_with_classification
--------------------------------
DROP TABLE IF EXISTS poi_with_classification;
CREATE TABLE IF NOT EXISTS poi_with_classification ENGINE = MergeTree()
ORDER BY (ref_no) AS
SELECT
    t1.ref_no,
    t1.pointx_class,
    t1.latitude,
    t1.longitude,
    stringToH3(t1.hex_id) AS hex_id_uint64,
    t2.firstdegreelabel AS poi_degree
FROM
    poi_uk AS t1
LEFT JOIN
    pointx_class_with_degree AS t2 ON t1.pointx_class = t2.pointxclassificationcode;

--------------------------------
-- label_closest_poi
--------------------------------
DROP TABLE IF EXISTS label_closest_poi;
CREATE TABLE IF NOT EXISTS label_closest_poi ENGINE = MergeTree()
ORDER BY (o_label, poi_degree) AS
SELECT
    hex.o_label,
    pwc_inner.ref_no AS closest_poi_ref_no,
    pwc_inner.poi_degree,
    round(geoDistance(hex.o_lon, hex.o_lat, pwc_inner.longitude, pwc_inner.latitude), 2) AS distance_to_poi
FROM
    label_hexring AS hex
INNER JOIN
    poi_with_classification AS pwc_inner ON hex.k_ring_hex_id = pwc_inner.hex_id_uint64
QUALIFY ROW_NUMBER() OVER (PARTITION BY hex.o_label, pwc_inner.poi_degree ORDER BY distance_to_poi ASC) = 1;


--------------------------------
--time weight

-- label_closest_poi
--     hex.o_label,
--     pwc_inner.ref_no AS closest_poi_ref_no,
--     pwc_inner.poi_degree,
--     round(geoDistance(hex.o_lon, hex.o_lat, pwc_inner.longitude, pwc_inner.latitude), 2) AS distance_to_poi


-- activity_weights
--     start_time String,
--     activity_type String,
--     type_weight Float64

-- SAs_test
--     start_time DateTime,
--     o_label String,

--------------------------------

DROP TABLE IF EXISTS stop_labels;
CREATE TABLE IF NOT EXISTS stop_labels ENGINE = MergeTree()
ORDER BY (o_label) AS
With filtered_sas AS (
    -- Step 2: Filter SAs_test data and prepare its H3 ID.
    SELECT DISTINCT userid, o_label, start_time
    FROM
        SAs_test
    WHERE
        activity_type = 'STATIONARY'
        AND home_activity = 'N'
        AND work_activity = 'N'
)
SELECT
    userid,
    o_label,
    start_time
FROM
    filtered_sas;
-- 8134656. rows

DROP TABLE IF EXISTS label_closest_poi_with_weight;
CREATE TABLE IF NOT EXISTS label_closest_poi_with_weight ENGINE = MergeTree()
ORDER BY (userid, o_label, start_time) AS
SELECT
    s.userid as userid,
    s.o_label as o_label,
    s.start_time as start_time,
    lcp.poi_degree AS poi_degree,
    lcp.closest_poi_ref_no,
    lcp.distance_to_poi,
    aw.type_weight
FROM
    stop_labels AS s
INNER JOIN
    label_closest_poi AS lcp
    ON s.o_label = lcp.o_label
INNER JOIN
    activity_weights AS aw
    ON aw.start_time = formatDateTime(toStartOfHour(s.start_time), '%H:%i:%S')
    AND aw.activity_type = lcp.poi_degree;
-- 269152155 rows
