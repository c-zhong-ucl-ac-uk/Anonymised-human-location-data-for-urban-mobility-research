import pandas as pd
import matplotlib.pyplot as plt
import src._plot_utils as pu

# Load the CSV file
df_hourly_activity = pd.read_csv(
    "data/data4report/yikang_2021Nov_hourly_user_stay_type_count.csv"
)

# Convert the date to datetime and extract the day of the week
df_hourly_activity["date"] = pd.to_datetime(
    df_hourly_activity["date"], format="%d/%m/%Y"
)
df_hourly_activity["day_of_week"] = df_hourly_activity["date"].dt.day_name()
df_hourly_activity["hour"] = pd.Categorical(
    df_hourly_activity["hour"], categories=range(24), ordered=True
)

# Remove outliers: first and last day of the month: Monday Nov 1 and Tuesday Nov 30
# df = df.drop(df[(df['date'] <= '2021-11-01') | (df['date'] >= '2021-11-30')].index)

# Remove outliers: first and last two days of the week: Monday Nov 1, Tuesday Nov 2, Monday Nov 29, Tuesday Nov 30
df_hourly_activity = df_hourly_activity.drop(
    df_hourly_activity[
        (df_hourly_activity["date"] <= "2021-11-02")
        | (df_hourly_activity["date"] >= "2021-11-29")
    ].index
)

# Define the days of the week in order
days_of_week = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

# Create subplots
fig, axs = plt.subplots(
    4,
    2,
    figsize=(18 * pu.cm, 20 * pu.cm),
    layout="constrained",
)
axs = axs.flatten()

for i, day in enumerate(days_of_week):
    day_df = df_hourly_activity[df_hourly_activity["day_of_week"] == day]

    home_user_count_stats = (
        day_df.groupby("hour", observed=False)["home_user_count"]
        .agg(["min", "max", "median"])
        .reset_index()
    )
    work_user_count_stats = (
        day_df.groupby("hour", observed=False)["work_user_count"]
        .agg(["min", "max", "median"])
        .reset_index()
    )
    other_user_count_stats = (
        day_df.groupby("hour", observed=False)["other_user_count"]
        .agg(["min", "max", "median"])
        .reset_index()
    )

    ax = axs[i]

    # Plotting the home user count
    color = "tab:blue"
    ax.set_ylabel("Home User Count", color=color, fontsize=8)
    ax.plot(
        home_user_count_stats["hour"].values,
        home_user_count_stats["median"].values,
        ms=3,
        label="Home User Median",
        color=color,
        marker="o",
    )
    ax.fill_between(
        home_user_count_stats["hour"],
        home_user_count_stats["min"],
        home_user_count_stats["max"],
        color=color,
        alpha=0.3,
        label="Home User Count Range",
    )

    ax.tick_params(axis="y", labelcolor="k")
    ax.ticklabel_format(axis="y", style="sci", scilimits=(0, 0))
    ax.set_ylim(ymin=0, ymax=5.5e5)

    # Creating a twin Axes sharing the x-axis for the work and other user counts
    ax2 = ax.twinx()

    ax2.set_ylabel("Work and Other User Count", fontsize=8)

    color = "tab:green"
    ax2.plot(
        work_user_count_stats["hour"].values,
        work_user_count_stats["median"].values,
        ms=3,
        label="Work User Count Median",
        color=color,
        marker="o",
    )
    ax2.fill_between(
        work_user_count_stats["hour"],
        work_user_count_stats["min"],
        work_user_count_stats["max"],
        color=color,
        alpha=0.3,
        label="Work User Count Range",
    )

    color = "tab:orange"
    ax2.plot(
        other_user_count_stats["hour"].values,
        other_user_count_stats["median"].values,
        ms=3,
        label="Other User Count Median",
        color=color,
        marker="o",
    )
    ax2.fill_between(
        other_user_count_stats["hour"],
        other_user_count_stats["min"],
        other_user_count_stats["max"],
        color=color,
        alpha=0.3,
        label="Other User Count Range",
    )

    ax2.tick_params(axis="y")
    ax2.ticklabel_format(axis="y", style="sci", scilimits=(0, 0))
    ax2.set_ylim(ymin=0, ymax=2.2e5)

    # Title for each subplot
    ax.set_title(day, fontsize=10)
    ax.spines["right"].set_visible(True)

# Legends
lines, labels = ax.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
axs[-1].legend(
    lines + lines2,
    labels + labels2,
    loc="center",
    facecolor="white",
    frameon=False,
    ncol=1,
)

# Hide the last subplot (used for legend)
axs[-1].axis("off")

# Set common labels
fig.text(0.5, 0.01, "Hour of The Day", ha="center", fontsize=12)
# fig.text(0.04, 0.5, 'User Count', va='center', rotation='vertical', fontsize=16)

# fig.suptitle('Hourly User Stay Location Type Count by Day of the Week', fontsize=20)
fig.tight_layout(rect=[0.01, 0.03, 1, 0.99])

# Save the figure with high resolution
plt.savefig("fig/fig5b_weekly.png", dpi=300)

# Display the plot
# plt.show()
