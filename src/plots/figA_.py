import pandas as pd
import matplotlib.pyplot as plt
import src._plot_utils as pu

# Load the CSV file for the first plot
df_hourly_activity = pd.read_csv(
    "data/data4report/yikang_hourly users and records nov 2021.csv"
)
# Convert the hour to a categorical variable to ensure proper ordering in the plot
df_hourly_activity["hour"] = pd.Categorical(
    df_hourly_activity["hour"], categories=range(24), ordered=True
)

# Remove outliers: 8am on November 7
df_hourly_activity = df_hourly_activity.drop(
    df_hourly_activity[
        (df_hourly_activity["hour"] == 8) & (df_hourly_activity["date"] == "07/11/2021")
    ].index
)

# Group the data by hour and calculate min, max, and median values
user_count_stats = (
    df_hourly_activity.groupby("hour", observed=False)["user_count"]
    .agg(["min", "max", "median"])
    .reset_index()
)
# Group the data by hour and calculate min, max, and median values
record_count_stats = (
    df_hourly_activity.groupby("hour", observed=False)["record_count"]
    .agg(["min", "max", "median"])
    .reset_index()
)

# Plot
# plt.rc("font", size=12)
fig, ax1 = plt.subplots(figsize=(18 * pu.cm, 10 * pu.cm), layout="constrained")

# Plotting the user count on the primary y-axis (left)
color = "tab:blue"
ax1.set_xlabel("Hour of The Day", fontsize=12)
ax1.set_ylabel("User Count", color=color, fontsize=12)
ax1.plot(
    user_count_stats["hour"],
    user_count_stats["median"],
    label="User Count Median",
    color=pu.colors[1],
    marker="o",
)
ax1.fill_between(
    user_count_stats["hour"],
    user_count_stats["min"],
    user_count_stats["max"],
    color=pu.colors[2],
    alpha=0.3,
    label="User Count Min-Max Range",
)
ax1.tick_params(axis="y", labelcolor=color)
ax1.ticklabel_format(axis="y", style="sci", scilimits=(0, 0))
ax1.set_ylim(ymin=0)

ax1.spines["right"].set_visible(True)

# Creating a twin Axes sharing the x-axis for the record count
ax2 = ax1.twinx()
color = "tab:red"
ax2.set_ylabel("Record Count", color=color, fontsize=12)
ax2.plot(
    record_count_stats["hour"],
    record_count_stats["median"],
    label="Record Count Median",
    color=pu.colors[-2],
    marker="o",
)
ax2.fill_between(
    record_count_stats["hour"],
    record_count_stats["min"],
    record_count_stats["max"],
    color=pu.colors[-3],
    alpha=0.1,
    label="Record Count Min-Max Range",
)
ax2.tick_params(axis="y", labelcolor=color)
ax2.ticklabel_format(axis="y", style="sci", scilimits=(0, 0))
ax2.set_ylim(ymin=0)

# plt.title('Hourly Number of Users and Records, 8-30 Nov 2021', fontsize=20)
# plt.grid(True)

# legends
lines, labels = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines + lines2, labels + labels2, loc="lower right", frameon=False)

# fig.tight_layout()

# Save the figure with high resolution
plt.savefig("fig/figA.png", dpi=300)

# Display the plot
# plt.show()
