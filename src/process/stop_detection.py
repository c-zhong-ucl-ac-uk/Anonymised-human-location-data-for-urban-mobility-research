from typing import Literal

import infostop
import numpy as np
import pandas as pd
from loguru import logger
import gc
from haversine import haversine_vector, Unit


def stop_detection(df_users):
    df_users = infostop_clustering(df_users, mode="multi_user", min_staying_time=300)
    # drop users with all nan labels
    mask = df_users.groupby("userid")["label"].transform(lambda x: x.notna().any())
    df_users = df_users[mask]

    df_trips = (
        df_users.groupby("userid")[["lat", "lon", "unix_timestamp", "label"]]
        .apply(lambda x: genTri(x))
        .reset_index()
        .drop(columns=["level_1", "lon", "lat"])
    )
    # # if max label < 3 drop the user
    # df_trips = df_trips.groupby("userid").filter(lambda x: x["label"].max() >= 3)
    del df_users
    return df_trips


def infostop_clustering(
    df,
    mode: Literal["single_user", "multi_user"] = "single_user",
    r1=50,
    r2=50,
    label_singleton=True,
    min_staying_time=60,
    max_time_between=86400,
    min_size=2,
    verbose=False,
):
    """
    infostop kwargs:
      r1=50,
      r2=50,
      label_singleton=True,
      min_staying_time=60,
      max_time_between=86400,
      min_size=2,
      verbose=False,
    """
    if len(df.index) <= 1:
        return df.assign(label=np.nan)

    model = infostop.Infostop(
        r1=r1,
        r2=r2,
        label_singleton=label_singleton,
        min_staying_time=min_staying_time,
        max_time_between=max_time_between,
        min_size=min_size,
        verbose=verbose,
    )
    try:
        if mode == "single_user":
            ls_data = df[["lat", "lon", "unix_timestamp"]].values
            labels = model.fit_predict([ls_data])[0]
            df["label"] = labels
            del ls_data
        else:
            df = df.sort_values(["userid", "unix_timestamp"])
            df = df.drop_duplicates(subset=["userid", "unix_timestamp"])

            # 每个用户的轨迹点序列
            groups = [
                g[["lat", "lon", "unix_timestamp"]].values
                for _, g in df.groupby("userid")
            ]
            labels = model.fit_predict(groups)

            # 展平并赋回
            df["label"] = np.concatenate(labels)

            # 内存释放
            del groups
            gc.collect()

        return df
    except Exception as e:
        logger.error(f"[ERROR] Clustering failed: {e}")
        return df.assign(label=np.nan)


def genTri(df):
    """
    df is labeled signals for each user
    df_stops:
            label        lat       lon  n_pnts
        0     16  51.411309 -0.147220    2582
        1    120  51.411446 -0.148522      10
        2    121  51.411932 -0.146910       2
    df_trips
    """
    if df.empty or df.shape[0] < 2:
        return pd.DataFrame()
    df_stays = (
        df[df.label != -1]
        .groupby("label")
        .agg(lat=("lat", "median"), lon=("lon", "median"), t_pnts=("label", "size"))
        .reset_index()
        .sort_values("t_pnts", ascending=False)  # total points in one label
    )

    df_stays["flabel"] = pd.factorize(df_stays["label"])[0] + 1
    trips = compute_intervals_with_count(
        df[["label"]].to_numpy(), df[["unix_timestamp"]].to_numpy()
    )

    # n_pts : n points in each stay or trip
    df_trips = pd.DataFrame(
        trips, columns=["label", "start_time", "end_time", "n_pnts"]
    )
    df_trips = df_trips.merge(df_stays, on="label", how="left")
    df_trips.loc[df_trips["label"] != -1, ["label"]] = df_trips["flabel"]
    df_trips = df_trips.drop(columns=["t_pnts", "flabel"])

    df_trips["start_time"] = pd.to_datetime(df_trips["start_time"], unit="s")
    df_trips["end_time"] = pd.to_datetime(df_trips["end_time"], unit="s")

    df_trips["o_lat"] = np.where(
        df_trips["label"] != -1, df_trips["lat"], df_trips["lat"].shift(1)
    )
    df_trips["o_lon"] = np.where(
        df_trips["label"] != -1, df_trips["lon"], df_trips["lon"].shift(1)
    )

    df_trips["d_lat"] = np.where(
        df_trips["label"] != -1, np.nan, df_trips["lat"].shift(-1)
    )
    df_trips["d_lon"] = np.where(
        df_trips["label"] != -1, np.nan, df_trips["lon"].shift(-1)
    )

    df_trips["o_label"] = np.where(
        df_trips["label"] != -1,
        df_trips["label"].astype("Int64"),
        df_trips["label"].shift(1).astype("Int64"),
    )
    df_trips["d_label"] = np.where(
        df_trips["label"] != -1,
        np.nan,
        df_trips["label"].shift(-1).astype("Int64"),
    )

    # 计算距离 更低内存速度更快
    mask = (df_trips["label"] == -1) & df_trips[
        ["o_lat", "o_lon", "d_lat", "d_lon"]
    ].notnull().all(axis=1)
    if mask.sum() == 0:
        df_trips["distance"] = 0.0

    else:
        coords_o = df_trips.loc[mask, ["o_lat", "o_lon"]].values
        coords_d = df_trips.loc[mask, ["d_lat", "d_lon"]].values

        df_trips.loc[mask, "distance"] = haversine_vector(
            coords_o, coords_d, Unit.METERS, comb=False
        )
        df_trips["distance"] = df_trips["distance"].fillna(0).round(2)

    # 计算活动持续时间
    df_trips["activity_duration"] = (
        df_trips["end_time"] - df_trips["start_time"]
    ).dt.total_seconds()

    del df_stays, trips
    return df_trips


def compute_intervals_with_count(labels, times, max_time_between=86400):
    """Compute stop and move intervals from the list of labels, with point counts.
    改进infostop方法，增加计数统计，修改if loc_prev == -1 才增加最后一个点的逻辑

    Parameters
    ----------
        labels: 1D np.array of integers
        times: 1D np.array of integers. `len(labels) == len(times)`.
        max_time_between: Maximum time allowed between consecutive points in the same segment (seconds)

    Returns
    -------
        intervals : list of [label, start_time, end_time, count]
    """
    assert len(labels) == len(times), "`labels` and `times` must match in length"

    # Stack input arrays for easy iteration
    trajectory = np.hstack([labels.reshape(-1, 1), times.reshape(-1, 1)])
    final_trajectory = []

    # Initialize first point
    loc_prev, t_start = trajectory[0]
    t_end = t_start
    count = 1

    # Iterate through the rest
    for loc, time in trajectory[1:]:
        if (loc == loc_prev) and ((time - t_end) < max_time_between):
            t_end = time
            count += 1
        else:
            final_trajectory.append([loc_prev, t_start, t_end, count])
            t_start = time
            t_end = time
            count = 1
        loc_prev = loc

    # Append the last segment
    final_trajectory.append([loc_prev, t_start, t_end, count])

    return final_trajectory
