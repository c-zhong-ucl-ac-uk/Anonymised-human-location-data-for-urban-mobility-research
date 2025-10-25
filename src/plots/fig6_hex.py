# fig6_hex.py 当前为空文件

import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from shapely.geometry import Polygon
import _plot_utils as pu


def create_hexagon_grid(gdf, hex_size=0.1):
    """Create a custom hexagon grid covering the study area"""
    bounds = gdf.total_bounds
    min_lng, min_lat, max_lng, max_lat = bounds

    # Calculate hexagon dimensions
    hex_width = hex_size
    hex_height = hex_size * np.sqrt(3) / 2

    hexagons = []
    hex_ids = []
    hex_id_counter = 0

    # Generate hexagonal grid
    y = min_lat
    row = 0
    while y < max_lat:
        x_offset = (hex_width * 0.75) * (row % 2)  # Offset every other row
        x = min_lng + x_offset

        while x < max_lng:
            # Create hexagon vertices
            vertices = []
            for i in range(6):
                angle = np.pi / 3 * i
                vertex_x = x + hex_width / 2 * np.cos(angle)
                vertex_y = y + hex_height / 2 * np.sin(angle)
                vertices.append((vertex_x, vertex_y))

            # Create polygon and check if it intersects with study area
            hex_polygon = Polygon(vertices)
            if hex_polygon.intersects(gdf.unary_union):
                hexagons.append(hex_polygon)
                hex_ids.append(f"hex_{hex_id_counter}")
                hex_id_counter += 1

            x += hex_width * 0.75

        y += hex_height
        row += 1

    hex_gdf = gpd.GeoDataFrame(
        {"hex_id": hex_ids, "geometry": hexagons}, crs="EPSG:4326"
    )

    return hex_gdf


def aggregate_od_to_hexagons(od_matrix, lad_gdf, hex_gdf):
    """Aggregate O-D matrix from LADs to hexagons"""
    # Find which hexagon each LAD centroid belongs to
    lad_centroids = lad_gdf.centroid
    lad_to_hex = {}

    for idx, centroid in lad_centroids.items():
        # Find the hexagon containing this centroid
        for hex_idx, hex_geom in hex_gdf.iterrows():
            if hex_geom.geometry.contains(centroid):
                lad_code = lad_gdf.loc[idx, "LAD21CD"]
                lad_to_hex[lad_code] = hex_geom["hex_id"]
                break

    # Aggregate O-D flows to hexagon level
    hex_od = {}

    for origin in od_matrix.index:
        for dest in od_matrix.columns:
            if origin in lad_to_hex and dest in lad_to_hex:
                hex_origin = lad_to_hex[origin]
                hex_dest = lad_to_hex[dest]

                if hex_origin not in hex_od:
                    hex_od[hex_origin] = {}
                if hex_dest not in hex_od[hex_origin]:
                    hex_od[hex_origin][hex_dest] = 0

                hex_od[hex_origin][hex_dest] += od_matrix.loc[origin, dest]

    return hex_od, lad_to_hex


def create_flow_lines(hex_gdf, hex_od, min_flow_threshold=100):
    """Create flow lines between hexagons"""
    flow_lines = []
    flow_values = []

    hex_centroids = hex_gdf.set_index("hex_id").geometry.centroid

    for origin_hex, destinations in hex_od.items():
        for dest_hex, flow in destinations.items():
            if flow >= min_flow_threshold and origin_hex != dest_hex:
                if (
                    origin_hex in hex_centroids.index
                    and dest_hex in hex_centroids.index
                ):
                    origin_point = hex_centroids.loc[origin_hex]
                    dest_point = hex_centroids.loc[dest_hex]

                    flow_lines.append(
                        {
                            "origin": origin_hex,
                            "destination": dest_hex,
                            "flow": flow,
                            "origin_geom": origin_point,
                            "dest_geom": dest_point,
                        }
                    )
                    flow_values.append(flow)

    return pd.DataFrame(flow_lines), flow_values


def calculate_hex_totals(hex_od):
    """Calculate total inflows and outflows for each hexagon"""
    hex_totals = {}

    # Calculate outflows
    for origin_hex, destinations in hex_od.items():
        if origin_hex not in hex_totals:
            hex_totals[origin_hex] = {"outflow": 0, "inflow": 0}
        hex_totals[origin_hex]["outflow"] = sum(destinations.values())

    # Calculate inflows
    for origin_hex, destinations in hex_od.items():
        for dest_hex, flow in destinations.items():
            if dest_hex not in hex_totals:
                hex_totals[dest_hex] = {"outflow": 0, "inflow": 0}
            hex_totals[dest_hex]["inflow"] += flow

    return hex_totals


def plot_hexagon_od_matrix(
    hex_gdf,
    hex_od,
    flow_df,
    hex_totals,
    title="Hexagon-based National O-D Matrix Visualization",
):
    """Create the main visualization"""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(
        2, 2, figsize=(20 * pu.cm, 20 * pu.cm), layout="constrained"
    )

    # 1. Hexagon grid with total flows
    total_flows = [
        hex_totals.get(hex_id, {"outflow": 0})["outflow"]
        for hex_id in hex_gdf["hex_id"]
    ]

    hex_gdf_plot = hex_gdf.copy()
    hex_gdf_plot["total_outflow"] = total_flows

    # Plot hexagons colored by total outflow
    hex_gdf_plot.plot(
        column="total_outflow",
        cmap="YlOrRd",
        ax=ax1,
        legend=True,
        linewidth=0.5,
        edgecolor="gray",
    )
    ax1.set_title("Total Outflows by Hexagon", fontsize=10)
    ax1.set_axis_off()

    # 2. Major flow lines
    if not flow_df.empty:
        # Select top flows for visualization
        top_flows = flow_df.nlargest(50, "flow")

        hex_gdf.plot(ax=ax2, color="lightgray", linewidth=0.5, edgecolor="gray")

        for _, flow in top_flows.iterrows():
            x_coords = [flow["origin_geom"].x, flow["dest_geom"].x]
            y_coords = [flow["origin_geom"].y, flow["dest_geom"].y]

            # Line width proportional to flow
            line_width = np.log10(flow["flow"]) * 0.5
            alpha = min(0.8, flow["flow"] / top_flows["flow"].max())

            ax2.plot(
                x_coords,
                y_coords,
                color=pu.colors[1],
                linewidth=line_width,
                alpha=alpha,
            )

        ax2.set_title("Major Flow Lines (Top 50)", fontsize=10)
        ax2.set_axis_off()

    # 3. Inflow visualization
    inflows = [
        hex_totals.get(hex_id, {"inflow": 0})["inflow"] for hex_id in hex_gdf["hex_id"]
    ]

    hex_gdf_plot["total_inflow"] = inflows
    hex_gdf_plot.plot(
        column="total_inflow",
        cmap="Blues",
        ax=ax3,
        legend=True,
        linewidth=0.5,
        edgecolor="gray",
    )
    ax3.set_title("Total Inflows by Hexagon", fontsize=10)
    ax3.set_axis_off()

    # 4. Flow balance (outflow - inflow)
    flow_balance = np.array(total_flows) - np.array(inflows)
    hex_gdf_plot["flow_balance"] = flow_balance

    hex_gdf_plot.plot(
        column="flow_balance",
        cmap="RdBu_r",
        ax=ax4,
        legend=True,
        linewidth=0.5,
        edgecolor="gray",
    )
    ax4.set_title("Flow Balance (Outflow - Inflow)", fontsize=10)
    ax4.set_axis_off()

    # Add main title
    fig.suptitle(title, fontsize=12, y=0.98)

    return fig


def main():
    """Main function to create hexagon-based O-D visualization"""
    print("Loading data...")

    # Load LAD boundaries
    lad_gdf = gpd.read_file("data/data4report/LAD.geojson")

    # Load O-D matrix (using census data as example)
    c_od = pd.read_csv("data/data4report/c_od.csv", index_col=0)

    # Filter LADs that exist in both datasets
    available_lads = set(lad_gdf["LAD21CD"]) & set(c_od.index) & set(c_od.columns)
    lad_gdf_filtered = lad_gdf[lad_gdf["LAD21CD"].isin(available_lads)]
    c_od_filtered = c_od.loc[list(available_lads), list(available_lads)]

    print(f"Working with {len(available_lads)} LADs")

    # Create hexagon grid
    print("Creating hexagon grid...")
    hex_gdf = create_hexagon_grid(lad_gdf_filtered, hex_size=0.3)

    # Filter hexagons that intersect with LADs
    hex_gdf = hex_gdf[hex_gdf.intersects(lad_gdf_filtered.unary_union)]

    print(f"Created {len(hex_gdf)} hexagons")

    # Aggregate O-D data to hexagons
    print("Aggregating O-D data to hexagons...")
    hex_od, lad_to_hex = aggregate_od_to_hexagons(
        c_od_filtered, lad_gdf_filtered.set_index("LAD21CD"), hex_gdf
    )

    # Create flow lines
    print("Creating flow lines...")
    flow_df, flow_values = create_flow_lines(hex_gdf, hex_od, min_flow_threshold=50)

    # Calculate hexagon totals
    hex_totals = calculate_hex_totals(hex_od)

    print(f"Generated {len(flow_df)} flow lines")

    # Create visualization
    print("Creating visualization...")
    fig = plot_hexagon_od_matrix(hex_gdf, hex_od, flow_df, hex_totals)

    # Save figure
    fig.savefig("fig/fig6_hexagon_od_matrix.png", dpi=300, bbox_inches="tight")
    print("Saved figure to fig/fig6_hexagon_od_matrix.png")

    # Print summary statistics
    print("\n=== Summary Statistics ===")
    print(f"Total hexagons: {len(hex_gdf)}")
    print(f"Total flows: {len(flow_df)}")
    if flow_values:
        print(f"Max flow: {max(flow_values):,.0f}")
        print(f"Mean flow: {np.mean(flow_values):,.0f}")
        print(f"Total flow volume: {sum(flow_values):,.0f}")


if __name__ == "__main__":
    main()
