# to geodataframe from database
import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from igraph import Graph
from tqdm import tqdm

import _plot_utils as pu
from _const import conn_duck

query = """
INSTALL spatial;
LOAD spatial;

DROP TABLE IF EXISTS gla_oa;

CREATE TABLE IF NOT EXISTS oa_lookup AS SELECT * FROM 'data/data4report/lookup_census.csv';

CREATE TABLE IF NOT EXISTS gla_oa AS SELECT * FROM ST_Read('/Users/adamzh0u/100_database/_boundary_london/london_oa_2021/oa_london.shp');


CREATE TABLE IF NOT EXISTS oa_trips_count AS
(
    WITH gla_oa_lookup AS (
        SELECT gla_oa.OA21CD, msoa21cd
        FROM gla_oa
        LEFT JOIN oa_lookup
        ON gla_oa.OA21CD = oa_lookup.oa21cd
    ),
    oa_trips AS (
        SELECT o_oa,d_oa
        FROM trj_2021nov
        WHERE o_oa in (select OA21CD from gla_oa_lookup)
        AND d_oa in (select OA21CD from gla_oa_lookup)
    ),
    mosa_trips AS (
    SELECT a.MSOA21CD as o_msoa, b.MSOA21CD as d_msoa
        FROM oa_trips
        LEFT JOIN gla_oa_lookup a
        ON oa_trips.o_oa = a.OA21CD
        LEFT JOIN gla_oa_lookup b
        ON oa_trips.d_oa = b.OA21CD
    )
    SELECT o_msoa, d_msoa, COUNT(*) as cnt
    FROM mosa_trips
    GROUP BY o_msoa, d_msoa
)
"""

conn_duck.query(query)

df_trips = conn_duck.query("SELECT * FROM oa_trips_count").df()
g = Graph.DataFrame(df_trips.dropna(), directed=False, use_vids=False)
gdf_msoa = gpd.GeoDataFrame.from_file("data/data4report/london_msoa_2021.shp")

ls = []

ls_res = [1, 5, 10]
for resolution in tqdm(ls_res):
    cres_leiden = Graph.community_leiden(
        g, objective_function="modularity", weights="cnt", resolution=resolution
    )
    ls.append(cres_leiden.membership)

df_clu = pd.DataFrame(ls).T
clu_names = [f"clu{i:.04f}" for i in ls_res]
df_clu.columns = clu_names

# assign index and merge
df_clu["id"] = g.vs["name"]

df_clu = df_clu.merge(gdf_msoa, left_on="id", right_on="msoa21cd")
gdf_clu = gpd.GeoDataFrame(df_clu, geometry="geometry")


fig, ax = plt.subplots(
    1, 3, figsize=(18 * pu.cm, 6 * pu.cm), dpi=300, layout="constrained"
)

for i in range(3):
    cmap = pu.shuffle_colormap("RdYlBu_r", n_colors=len(gdf_clu))
    gdf_clu.plot(
        column=f"clu{ls_res[i]:.04f}",
        cmap=cmap,
        legend=False,
        ax=ax[i],
        linewidth=0.03,
        edgecolor="black",
    )
    ax[i].set_title(f"Resolution {ls_res[i]}")
    ax[i].set_axis_off()

fig.savefig("fig/fig5_community_detection.png", dpi=1500)
# fig.savefig("fig/fig5_community_detection.pdf", dpi=1500)
