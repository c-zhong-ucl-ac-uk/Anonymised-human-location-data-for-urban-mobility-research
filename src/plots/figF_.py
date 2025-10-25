from src.fig4_LAD_residents_corr import *

plot_correlation(
    mobile_pop_msoa[mobile_pop_msoa["count_m"] > 10],
    "count_m",
    "count_c",
    "MSOA-Level Pearson Correlation between Mobile Phone App Data and Census Data ",
    "The number of users in Mobile Phone App Data",
    "Number of people in Census Data",
    False,
)
