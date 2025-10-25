import pandas as pd
import numpy as np
import geopandas as gpd
from scipy.stats import spearmanr
from skimage.metrics import structural_similarity as ssim
import matplotlib.pyplot as plt
import _plot_utils as pu
import os
from pathlib import Path


def save_intermediate_results(df, filename, cache_dir="cache"):
    """Save intermediate results to cache"""
    Path(cache_dir).mkdir(exist_ok=True)
    df.to_parquet(f"{cache_dir}/{filename}.parquet")


def load_intermediate_results(filename, cache_dir="cache"):
    """Load intermediate results from cache if available"""
    filepath = f"{cache_dir}/{filename}.parquet"
    if os.path.exists(filepath):
        return pd.read_parquet(filepath)
    return None


def load_intermediate_gdf(filename, cache_dir="cache"):
    """Load intermediate results from cache if available"""
    filepath = f"{cache_dir}/{filename}.parquet"
    if os.path.exists(filepath):
        return gpd.read_parquet(filepath)
    return None


def load_data(census_file, mobile_file, msoa_map_file):
    """Load and prepare initial dataframes"""
    print("Loading raw data...")
    df_census = pd.read_csv(census_file)
    df_mobile = pd.read_csv(mobile_file)
    df_map = pd.read_csv(msoa_map_file)

    la_ids = df_map[["LTLA22CD", "LTLA22NM"]].drop_duplicates()
    return df_census, df_mobile, df_map, la_ids


def get_msoas(la, df_map):
    """Get MSOAs for a given local authority"""
    return df_map[df_map["LTLA22CD"] == la]["MSOA21CD"]


def create_od_matrix(data, msoas, home_col, work_col, count_col, cids):
    """Create and fill OD matrix for selected MSOAs"""
    # Filter flow data
    selected = data[(data[home_col].isin(msoas)) & (data[work_col].isin(msoas))]

    # Aggregate flow data
    matrix = (
        selected.groupby([home_col, work_col])[count_col].sum().unstack(fill_value=0)
    )

    # Create standardized matrix
    std_matrix = pd.DataFrame(0, index=cids, columns=cids)

    # Fill matrix
    for idx, row in matrix.iterrows():
        for col, value in row.items():
            if col in std_matrix.columns:
                std_matrix.loc[idx, col] = value

    return std_matrix


def calculate_metrics(c_matrix, m_matrix):
    """Calculate correlation metrics between census and mobile matrices"""
    # Convert matrices to 1D and apply log transform
    c_list = [value for row in c_matrix.itertuples() for value in row[1:]]
    m_list = [value for row in m_matrix.itertuples() for value in row[1:]]

    c_list = np.log1p(c_list)
    m_list = np.log1p(m_list)

    # Calculate correlations
    pearson_corr = np.corrcoef(c_list, m_list)[0, 1]
    spearman_corr, p_value = spearmanr(c_list, m_list)

    # Calculate SSIM
    if c_matrix.shape[0] > 2:
        ss = ssim(
            c_matrix.values,
            m_matrix.values,
            data_range=m_matrix.values.max() - m_matrix.values.min(),
            win_size=3,
        )
    else:
        ss = 0

    # Calculate totals and ratio
    c_sum = np.sum(c_matrix.values)
    m_sum = np.sum(m_matrix.values)
    mc_ratio = m_sum / c_sum if c_sum != 0 else 0

    return {
        "pearson": round(pearson_corr, 3),
        "spearman": round(spearman_corr, 3),
        "spearman_p": round(p_value, 3),
        "ssim": round(ss, 3),
        "census_total": c_sum,
        "mobile_total": m_sum,
        "ratio": round(mc_ratio, 3),
    }


def analyze_local_authorities(
    df_census, df_mobile, df_map, la_ids, force_compute=False
):
    """Analyze OD matrices with caching"""
    # Try to load from cache
    cache_file = "la_analysis_results"
    if not force_compute:
        cached_results = load_intermediate_results(cache_file)
        if cached_results is not None:
            print("Loading results from cache...")
            return cached_results

    print("Computing LA analysis...")
    results = []
    for _, row in la_ids.iterrows():
        # Get MSOAs for current LA
        msoas = get_msoas(row["LTLA22CD"], df_map)

        # Get census data for these MSOAs
        c_selected = df_census[
            df_census["Middle layer Super Output Areas code"].isin(msoas)
        ]
        cids = c_selected["Middle layer Super Output Areas code"].unique()

        # Create matrices
        c_matrix = create_od_matrix(
            df_census,
            msoas,
            "Middle layer Super Output Areas code",
            "MSOA of workplace code",
            "Count",
            cids,
        )

        m_matrix = create_od_matrix(
            df_mobile, msoas, "MSOA21CD_home", "MSOA21CD_work", "count", cids
        )

        # Calculate metrics
        metrics = calculate_metrics(c_matrix, m_matrix)

        # Compile results
        results.append(
            [
                row["LTLA22CD"],
                row["LTLA22NM"],
                metrics["pearson"],
                metrics["spearman"],
                metrics["spearman_p"],
                metrics["ssim"],
                metrics["census_total"],
                metrics["mobile_total"],
                metrics["ratio"],
                len(cids),
                len(msoas),
            ]
        )

    df_results = pd.DataFrame(
        results,
        columns=[
            "LTLA22CD",
            "LTLA22NM",
            "Pearson",
            "Spearman",
            "Spearman_p_value",
            "SSIM",
            "Census_Total",
            "Mobile_Total",
            "Ratio",
            "Census_Areas_Count",
            "Mobile_Areas_Count",
        ],
    )

    # Save results to cache
    save_intermediate_results(df_results, cache_file)
    return df_results


def prepare_map_data(df_hourly_activity, force_compute=False):
    """Prepare map data with caching"""
    cache_file = "prepared_map_data"
    if not force_compute:
        cached_data = load_intermediate_gdf(cache_file)
        if cached_data is not None:
            print("Loading map data from cache...")
            return cached_data

    print("Preparing map data...")
    # Load and process map data
    lad = gpd.read_file("data/data4report/LAD.geojson")
    merged_gdf = lad.merge(
        df_hourly_activity, left_on="LAD21CD", right_on="LTLA22CD", how="left"
    )

    lookup = pd.read_csv("data/data4report/lookup_census.csv")
    lad_list = lookup.ladcd.unique()
    merged_gdf = merged_gdf[merged_gdf["LAD21CD"].isin(lad_list)]
    merged_gdf.fillna(0, inplace=True)
    merged_gdf = merged_gdf[merged_gdf["Pearson"] > 0]

    # Save to cache
    save_intermediate_results(merged_gdf, cache_file)
    return merged_gdf


def create_correlation_maps(
    merged_gdf,
    variables,
    cmap_name="coolwarm",
    output_file="fig/Fig3_spatial_correlation.png",
):
    """Create and save correlation maps"""
    print("Creating correlation maps...")
    # Calculate value ranges
    vmins = {var: np.nanmin(merged_gdf[var][merged_gdf[var] != 0]) for var in variables}
    vmaxs = {var: merged_gdf[var].max() for var in variables}
    lad = gpd.read_file("data/data4report/LAD.geojson")
    # Create figure
    fig, axes = plt.subplots(
        1, len(variables), figsize=(18 * pu.cm, 14 * pu.cm), layout="constrained"
    )

    # Ensure axes is always a list
    if len(variables) == 1:
        axes = [axes]

    # Plot each variable
    for i, var in enumerate(variables):
        ax = axes[i]

        # Plot choropleth
        merged_gdf.plot(
            ax=ax,
            column=var,
            cmap=pu.colormap,
            linewidth=0.001,
            edgecolor="0",
            zorder=2,
        )
        lad.plot(ax=ax, facecolor="none", edgecolor="black", linewidth=0.05, zorder=3)

        # Set title and format
        tvar = "Pearson Correlation" if var == "Pearson" else "Ratio"
        ax.set_title(tvar, fontsize=10)
        ax.tick_params(
            left=False, right=False, labelleft=False, labelbottom=False, bottom=False
        )
        ax.tick_params(labelsize=7)
        ax.grid(False)
        ax.spines[["right", "top"]].set_visible(True)
        ax.set_ylim(10_000, 700_000)
        ax.set_xlim(100_000, 660_000)

        # Add colorbar
        sm = plt.cm.ScalarMappable(
            cmap=pu.colormap, norm=plt.Normalize(vmin=vmins[var], vmax=vmaxs[var])
        )
        sm._A = []
        cbar = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.02)
        cbar.ax.tick_params(direction="out")
        for t in cbar.ax.get_yticklabels():
            t.set_fontsize(8)
        # add scale bar
        from matplotlib_scalebar.scalebar import ScaleBar

        ax.add_artist(ScaleBar(1, location="lower right"))

        # add north arrow
        x, y, arrow_length = 0.95, 0.98, 0.1
        ax.annotate(
            "N",
            xy=(x, y),
            xytext=(x, y - arrow_length),
            arrowprops=dict(facecolor="black", width=2, headwidth=6),
            ha="center",
            va="center",
            fontsize=7,
            xycoords=ax.transAxes,
        )

    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    plt.savefig(output_file, dpi=1500, bbox_inches="tight")
    plt.close()
    print(f"Figure saved to {output_file}")


def main(force_compute=False):
    """Main function with caching control"""
    # 加载原始数据
    df_census, df_mobile, df_map, la_ids = load_data(
        "data/data4report/ODWP01EW_MSOA.csv",
        "data/data4report/MSOA_county_home_work.csv",
        "data/data4report/MSOA_(2021)_to_Ward_to_Lower_Tier_Local_Authority_(May_2022)_Lookup_for_England_and_Wales.csv",
    )

    # 分析数据
    df_hourly_activity = analyze_local_authorities(
        df_census, df_mobile, df_map, la_ids, force_compute=force_compute
    )
    df_hourly_activity = df_hourly_activity[df_hourly_activity["Pearson"] > 0]

    # 准备地图数据
    merged_gdf = prepare_map_data(df_hourly_activity, force_compute=force_compute)

    # 创建相关性地图
    create_correlation_maps(merged_gdf, ["Pearson", "Ratio"])


if __name__ == "__main__":
    # 使用方法：
    # force_compute=True 强制重新计算
    # force_compute=False 使用缓存（如果有）
    main(force_compute=False)
