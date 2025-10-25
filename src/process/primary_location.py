import pandas as pd
import pendulum


def calculate_nighttime_overlap(start: pd.Timestamp, end: pd.Timestamp) -> float:
    """
    使用 pendulum 计算事件在夜间（21:00 - 次日07:00）时段内的重叠时间

    参数:
        start (pendulum.DateTime): 事件开始时间
        end (pendulum.DateTime): 事件结束时间

    返回:
        pendulum.Duration: 重叠的总时长 seconds
    """
    start = pendulum.instance(start)
    end = pendulum.instance(end)
    total_overlap = pendulum.duration()

    current_day = start.start_of("day")

    while current_day <= end.start_of("day"):
        # 定义夜间区间：21:00 到 次日07:00
        night_start = current_day.add(hours=21)
        night_end = current_day.add(days=1).add(hours=7)

        # 计算当前夜间时段与事件的交集
        interval_start = max(start, night_start)
        interval_end = min(end, night_end)

        if interval_start < interval_end:
            total_overlap += interval_end - interval_start

        current_day = current_day.add(days=1)

    return total_overlap.total_seconds()


def calculate_workday_overlap(start: pd.Timestamp, end: pd.Timestamp) -> float:
    """
    使用 pendulum 计算事件在工作日（08:00 - 17:00）时段内的重叠时间（单位：秒）

    参数:
        start (pd.Timestamp): 事件开始时间
        end (pd.Timestamp): 事件结束时间

    返回:
        float: 重叠的总时长（秒）
    """
    start = pendulum.instance(start)
    end = pendulum.instance(end)
    total_overlap = pendulum.duration()

    current_day = start.start_of("day")

    while current_day <= end.start_of("day"):
        if current_day.weekday() < 5:  # workday check
            work_start = current_day.add(hours=8)
            work_end = current_day.add(hours=17)

            interval_start = max(start, work_start)
            interval_end = min(end, work_end)

            if interval_start < interval_end:
                total_overlap += interval_end - interval_start

        current_day = current_day.add(days=1)

    return total_overlap.total_seconds()


def method_1(df_data):
    df_filtered = df_data.loc[
        df_data["label"] != -1, ["start_time", "end_time", "label"]
    ].copy()

    if len(df_filtered) == 0:
        return df_data

    df_filtered["home_activity_duration"] = df_filtered.apply(
        lambda row: calculate_nighttime_overlap(row["start_time"], row["end_time"]),
        axis=1,
    )

    df_filtered["work_activity_duration"] = df_filtered.apply(
        lambda row: calculate_workday_overlap(row["start_time"], row["end_time"]),
        axis=1,
    )

    # Group by label and sum activity_duration, then find the index(label) with maximum sum

    home_label = df_filtered.groupby("label")["home_activity_duration"].sum().idxmax()
    df_data.loc[df_data["label"] == home_label, "home_activity"] = "Y"

    df_filtered_home = df_filtered[df_filtered["label"] != home_label]

    if len(df_filtered_home) > 0:
        work_label = (
            df_filtered_home.groupby("label")["work_activity_duration"].sum().idxmax()
        )
        df_data.loc[df_data["label"] == work_label, "work_activity"] = "Y"

    del df_filtered, df_filtered_home
    return df_data


def add_primary_locations(df_users, method="method_1"):
    df_users["home_activity"] = "N"
    df_users["work_activity"] = "N"
    if method == "method_1":
        df_users = (
            df_users.groupby("userid")[df_users.columns.tolist()]
            .apply(method_1)
            .reset_index(drop=True)
        )
    return df_users
