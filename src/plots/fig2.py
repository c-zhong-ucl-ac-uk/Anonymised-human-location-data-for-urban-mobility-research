import pandas as pd
import numpy as np
import seaborn as sns
from scipy import optimize
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from scipy.interpolate import interp1d
from scipy.stats import linregress
import matplotlib.ticker as ticker
from joblib import Memory

# self defined modules
import _plot_utils as pu
from _const import conn_duck

# ============ Data ============
# Define the SQL query using parquet_scan
sql_query = """
CREATE TABLE IF NOT EXISTS hourly_activity_summary AS
WITH activity_summary AS (
    SELECT
        CAST(start_time AS DATE) AS date,
        strftime('%A', start_time) AS day,
        CAST(strftime('%H', start_time) AS INTEGER) AS hr,
        COUNT(*) AS activity_count
    FROM trj_2021nov AS activities
    GROUP BY CAST(start_time AS DATE), strftime('%A', start_time), CAST(strftime('%H', start_time) AS INTEGER)
)

SELECT
    hr,
    CAST(AVG(CASE WHEN day = 'Monday' THEN activity_count ELSE NULL END) AS INTEGER) AS Monday,
    CAST(AVG(CASE WHEN day = 'Tuesday' THEN activity_count ELSE NULL END) AS INTEGER) AS Tuesday,
    CAST(AVG(CASE WHEN day = 'Wednesday' THEN activity_count ELSE NULL END) AS INTEGER) AS Wednesday,
    CAST(AVG(CASE WHEN day = 'Thursday' THEN activity_count ELSE NULL END) AS INTEGER) AS Thursday,
    CAST(AVG(CASE WHEN day = 'Friday' THEN activity_count ELSE NULL END) AS INTEGER) AS Friday,
    CAST(AVG(CASE WHEN day = 'Saturday' THEN activity_count ELSE NULL END) AS INTEGER) AS Saturday,
    CAST(AVG(CASE WHEN day = 'Sunday' THEN activity_count ELSE NULL END) AS INTEGER) AS Sunday
FROM activity_summary
GROUP BY hr
ORDER BY hr;
"""
conn_duck.execute(sql_query)
df_hourly_activity = conn_duck.execute("SELECT * FROM hourly_activity_summary").df()

## ================ data 2 ================

conn_duck.execute(sql_query)
df_distance = conn_duck.execute("SELECT * FROM distance_summary").df()

# Define a directory to store the cache
memory = Memory("cache_directory", verbose=0)


# Decorate the function that processes the data with @memory.cache
@memory.cache
def get_edata():
    sql_query2 = "CREATE TABLE IF NOT EXISTS distance_summary AS (select distance from trj_2021nov where distance > 0);"
    conn_duck.execute(sql_query2)
    df_distance = conn_duck.execute("SELECT * FROM distance_summary").df()
    df_trips = df_distance.dropna()
    edata = df_trips.loc[df_trips["distance"] > 1000, "distance"].tolist()
    data = [round(i / 1000, 3) for i in edata]

    x = np.logspace(min(np.log10(data)), max(np.log10(data)), 100)
    hist, bin_edges = np.histogram(data, bins=x)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    p_hist = hist / sum(hist)
    return bin_centers, p_hist


# Use the cached function
bin_centers, p_hist = get_edata()


## ================ data 3 ================
# Decorate the function that processes the data with @memory.cache
@memory.cache
def process_home_work_data():
    query3 = """
    CREATE TABLE IF NOT EXISTS home_work_locations AS
    SELECT userid, activity_type, home_activity, work_activity, o_lat, o_lon, o_oa
    FROM trj_2021nov
    WHERE activity_type != 'NON_STATIONARY' AND (home_activity = 'Y' OR work_activity = 'Y')
    """
    conn_duck.execute(query3)
    df_hw = conn_duck.execute("SELECT * FROM home_work_locations").df()
    lookup = pd.read_csv("data/data4report/lookup_census.csv")

    home_df = df_hw[df_hw["home_activity"] == "Y"][["userid", "o_oa"]]
    home_df = home_df.drop_duplicates(subset="userid").reset_index(drop=True)
    home_gdf = pd.merge(home_df, lookup, left_on="o_oa", right_on="oa21cd", how="left")

    mobile_pop_lad = (
        home_gdf.groupby("ladcd")
        .agg({"userid": "size"})
        .rename(columns={"userid": "count"})
        .reset_index()
    )

    census_pop = pd.read_csv("data/data4report/census_pop2021.csv")
    census_pop_msoa = pd.merge(
        census_pop, lookup, left_on="mnemonic", right_on="msoa21cd", how="left"
    )
    census_pop_lad = (
        census_pop_msoa.groupby("ladcd")
        .agg({"Total: All usual residents": "sum"})
        .rename(columns={"Total: All usual residents": "count"})
        .reset_index()
    )

    mobile_pop_lad = pd.merge(census_pop_lad, mobile_pop_lad, on="ladcd", how="left")
    mobile_pop_lad.columns = ["ladcd", "count_c", "count_m"]
    mobile_pop_lad["rate"] = mobile_pop_lad["count_m"] * 1.0 / mobile_pop_lad["count_c"]

    filtered_lad = mobile_pop_lad[mobile_pop_lad["count_m"] > 100]
    return filtered_lad


# Use the cached function
filtered_lad = process_home_work_data()

# ============ Plot ============
# Create figure and gridspec
fig = plt.figure(layout="constrained", figsize=(18 * pu.cm, 11 * pu.cm))
gs1 = gridspec.GridSpec(1, 1, figure=fig, bottom=0.55)
ax1 = fig.add_subplot(gs1[0])

gs2 = gridspec.GridSpec(1, 2, figure=fig, top=0.55, wspace=0.1)
ax2 = fig.add_subplot(gs2[0])
ax3 = fig.add_subplot(gs2[1])

days = df_hourly_activity.columns[1:].tolist()
n_days = len(days)

for n in range(n_days):
    x = df_hourly_activity["hr"].values
    y = df_hourly_activity[days[n]].values
    f = interp1d(x, y, kind="cubic")
    xnew = np.linspace(0, 23, num=100, endpoint=True)
    ynew = f(xnew)
    ax1.plot(xnew, ynew, "-", color=pu.colors[n], alpha=1, linewidth=1, label=days[n])

ax1.legend(fontsize=8, frameon=False, loc="upper left")
ax1.set_xlim(0, 23)
ax1.set_ylim(-50_000, 700_000)
ax1.set_xticks(range(0, 24, 2))
ax1.set_xticklabels(range(0, 24, 2))
ax1.set_yticks(np.arange(0, 800_000, 100_000))
ax1.set_yticklabels([f"{int(label / 1000):,.0f}K" for label in ax1.get_yticks()])
ax1.set_xlabel("Hour of the Day", fontsize=10)
ax1.set_ylabel("Activity Count", fontsize=10)
print("Plot (a) completed")


# ============ Plot 2 ============
def log_tpl_08gonz(x, d0=1.5, d1=80, a=1.75):
    y = -a * np.log(x + d0) - x / d1
    return y


p0 = [3, 100, 1.2]
popt, pcov = optimize.curve_fit(
    log_tpl_08gonz, bin_centers, np.log(p_hist), p0=p0, maxfev=10000
)
fit_tpl_08gonz = np.exp(log_tpl_08gonz(bin_centers, *popt))

ax2.scatter(bin_centers, p_hist, label="Empirical data", s=3, color=pu.colors[2])
ax2.plot(
    bin_centers,
    fit_tpl_08gonz,
    color=pu.colors[0],
    label=f"$P(\Delta d) = (d+{popt[0]:.2f})^{{-{popt[2]:.2f}}}e^{{-d/{popt[1]:.0f}}}$",
)
ax2.set_yscale("log")
ax2.set_xscale("log")
ax2.set_xlabel("$\Delta d/km$", fontsize=10)
ax2.set_ylabel("$P(\Delta d)$", fontsize=10)
ax2.legend(frameon=False, loc="lower left", fontsize=8)
ax2.xaxis.set_minor_locator(ticker.LogLocator(numticks=999, subs="auto"))
ax2.yaxis.set_minor_locator(ticker.LogLocator(numticks=999, subs="auto"))

print("Plot (b) completed")

# ============ Plot 3 ============
sns.regplot(
    x="count_m",
    y="count_c",
    data=filtered_lad,
    scatter_kws={"s": 10},
    line_kws={"color": "black"},
    ax=ax3,
)

ax3.set_xscale(
    "log",
)
ax3.set_yscale(
    "log",
)
ax3.set_xlabel("Number of users", fontsize=10)
ax3.set_ylabel("Number of people", fontsize=10)
ax3.set_xlim(500, 10_000)
ax3.grid(False)

pearson_corr = filtered_lad["count_m"].corr(filtered_lad["count_c"])
slope, intercept, r_value, p_value, std_err = linregress(
    filtered_lad["count_m"], filtered_lad["count_c"]
)
textstr = f"Pearson correlation = {pearson_corr:.3f}\np_value = {p_value:.3f}"

ax3.text(
    0.45,
    0.05,
    textstr,
    transform=ax3.transAxes,
    fontsize=8,
)
print("Plot (c) completed")

## ================ plot label ================
for i in range(3):
    ax = [ax1, ax2, ax3][i]
    if i == 0:  # 第一个图（上方的大图）
        x_pos = -0.075
    else:  # 下方的两个小图
        x_pos = -0.15

    ax.text(
        x_pos,
        1.01,
        f"{chr(97 + i)}",
        weight="bold",
        transform=ax.transAxes,
        fontsize=12,
        ha="left",
        va="bottom",
    )

gs1.tight_layout(fig, pad=0.1)
gs1.update(left=0.05, right=0.95, bottom=0.55)
gs2.tight_layout(fig, pad=0.1)
gs2.update(left=0.05, right=0.95, top=0.43, wspace=0.2)

plt.tight_layout()
# Save the combined figure
plt.savefig("fig/Fig2_combined.png", dpi=300, bbox_inches="tight")
plt.savefig("fig/Fig2_combined.pdf", bbox_inches="tight")
