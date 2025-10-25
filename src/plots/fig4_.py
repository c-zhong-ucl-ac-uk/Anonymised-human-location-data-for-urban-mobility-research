from spint import Gravity, Production, Attraction, Doubly
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import _plot_utils as pu

jobs = pd.read_csv("data/data4report/lookup_census.csv", index_col=1)

jobs = pd.read_csv("data/data4report/lads_jobs_2021.csv", index_col=1)
pop = pd.read_csv("data/data4report/lads_jobs_pop_2021.csv", index_col=0)
pop.index = pop["Area code"]

m_od = pd.read_csv("data/data4report/m_od.csv", index_col=0)
c_od = pd.read_csv("data/data4report/c_od.csv", index_col=0)

distance_df = pd.read_csv("data/data4report/dist.csv")
distance_df.set_index(["from", "to"], inplace=True)


def process_od(od, distance_df, pop, jobs):
    dij = []
    flows = []
    Origin = []
    Destination = []
    Oi = []
    Dj = []

    for i in od.columns.values:
        for j in od.index.values:
            if i != j:
                flows.append(od.loc[i, j])
                dij.append(distance_df.loc[(i, j), "distance"])
                Origin.append(i)
                Destination.append(j)
                if i in pop.index:
                    Oi.append(int(pop.loc[i]["In employment 2021"].replace(",", "")))
                else:
                    Oi.append(0.1)

                if j in jobs.index:
                    Dj.append(int(jobs.loc[j]["Total jobs"].replace(",", "")))
                else:
                    Dj.append(0.1)

    dij = np.array(dij)
    flows = np.array(flows)
    Oi = np.array(Oi)
    Dj = np.array(Dj)
    dij = np.array(dij)
    Origin = np.array(Origin)
    Destination = np.array(Destination)

    return dij, flows, Origin, Destination, Oi, Dj


def calculate_params(flows, Oi, Dj, dij, Origin=None, Destination=None, func="pow"):
    grav = Gravity(flows, Oi, Dj, dij, cost_func=func)
    prod = Production(flows, Origin, Dj, dij, cost_func=func)
    attr = Attraction(flows, Destination, Oi, dij, cost_func=func)
    doub = Doubly(flows, Origin, Destination, dij, cost_func=func)

    return grav, prod, attr, doub


def process_models(models):
    R2, adjR2, SSI, SRMSE, AIC = [], [], [], [], []
    model_name = ["Gravity", "Production", "Attraction", "Doubly"]

    for model in models:
        R2.append(round(model.pseudoR2, 2))
        adjR2.append(round(model.adj_pseudoR2, 2))
        SSI.append(round(model.SSI, 2))
        SRMSE.append(round(model.SRMSE, 2))
        AIC.append(round(model.AIC, 2))

    cols = {
        "model_name": model_name,
        "R2": R2,
        "adjR2": adjR2,
        "SSI": SSI,
        "SRMSE": SRMSE,
        "AIC": AIC,
    }

    data = pd.DataFrame(cols).set_index("model_name")
    return data


def process_params(models):
    model_names = np.array(["Gravity", "Production", "Attraction", "Doubly"]).reshape(
        -1, 1
    )

    params1 = np.round(models[0].params[-4:].T, 3)
    params2 = np.round(models[1].params[-4:].T, 3)
    params3 = np.round(models[2].params[-4:].T, 3)
    params4 = np.round(models[3].params[-4:].T, 3)

    result = np.vstack((params1, params2, params3, params4))
    return np.hstack((model_names, result))


def process_tvalues(models):
    model_names = np.array(["Gravity", "Production", "Attraction", "Doubly"]).reshape(
        -1, 1
    )

    params1 = np.round(models[0].tvalues[-4:].T, 3)
    params2 = np.round(models[1].tvalues[-4:].T, 3)
    params3 = np.round(models[2].tvalues[-4:].T, 3)
    params4 = np.round(models[3].tvalues[-4:].T, 3)

    result = np.vstack((params1, params2, params3, params4))
    return np.hstack((model_names, result))


def run_model(od, pop, jobs, dist, func=None):
    dij, flows, Origin, Destination, Oi, Dj = process_od(od, dist, pop, jobs)
    grav, prod, attr, doub = calculate_params(
        flows, Oi, Dj, dij, Origin, Destination, func=func
    )
    data = process_models([grav, prod, attr, doub])
    params = process_params([grav, prod, attr, doub])
    params = pd.DataFrame(params, columns=["model", "k", "µ", "α", "β"])
    return params, data


def get_params(od, pop, jobs, dist, func=None):
    dij, flows, Origin, Destination, Oi, Dj = process_od(od, dist, pop, jobs)
    grav, prod, attr, doub = calculate_params(
        flows, Oi, Dj, dij, Origin, Destination, func=func
    )
    return grav, prod, attr, doub


dij, flows, Origin, Destination, Oi, Dj = process_od(c_od, distance_df, pop, jobs)
# Exponential-based gravity models using census OD
p_c_exp, d_c_exp = run_model(c_od, pop, jobs, distance_df, func="exp")

# Exponential-based gravity models using mobile app OD
p_m_exp, d_m_exp = run_model(m_od, pop, jobs, distance_df, func="exp")

# Power-based gravity models using census OD
p_c_pow, d_c_pow = run_model(c_od, pop, jobs, distance_df, func="pow")

# Power-based gravity models using mobile OD
p_m_pow, d_m_pow = run_model(m_od, pop, jobs, distance_df, func="pow")

# Create subplots for the first figure (data1 and data2)
fig1, axs1 = plt.subplots(
    1, 2, figsize=(18 * pu.cm, 8 * pu.cm), layout="constrained"
)  # 1 row, 2 columns

# Set up bar positions
x = np.arange(len(d_c_pow.index))  # Label locations
width = 0.35  # Width of bars

# Plotting for Census OD and Mobile OD with power cost function
bars1 = axs1[0].bar(
    x - width / 2,
    d_c_pow["R2"].values,
    width,
    color=pu.colors[1],
    label="Census OD",
)
bars2 = axs1[0].bar(
    x + width / 2,
    d_m_pow["R2"].values,
    width,
    color=pu.colors[-2],
    label="Mobile OD",
)
axs1[0].set_xlabel("Cost function = pow", fontsize=10)
axs1[0].set_ylabel("$R^2$", fontsize=10)
axs1[0].set_xticks(x)
axs1[0].set_xticklabels(d_c_pow.index, fontsize=8)
axs1[0].legend(loc="upper left", fontsize=8, frameon=False)
axs1[0].set_ylim(0, 1.15)  # Set y-axis limits to range from 0 to 1
axs1[0].tick_params(axis="both", which="major", labelsize=8)

# Annotate bars with their R2 values
for i, (bar1, bar2) in enumerate(zip(bars1, bars2)):
    height1 = bar1.get_height()
    height2 = bar2.get_height()
    axs1[0].annotate(
        f"{height1:.2f}",
        xy=(bar1.get_x() + bar1.get_width() / 2, height1),
        xytext=(0, 3),
        textcoords="offset points",
        ha="center",
        fontsize=8,
    )
    axs1[0].annotate(
        f"{height2:.2f}",
        xy=(bar2.get_x() + bar2.get_width() / 2, height2),
        xytext=(0, 3),
        textcoords="offset points",
        ha="center",
        fontsize=8,
    )

# Plotting for Census OD and Mobile OD with exponential cost function
bars3 = axs1[1].bar(
    x - width / 2,
    d_c_exp["R2"].to_numpy(),
    width,
    color=pu.colors[1],
    label="Census OD",
)
bars4 = axs1[1].bar(
    x + width / 2,
    d_m_exp["R2"].to_numpy(),
    width,
    color=pu.colors[-2],
    label="Mobile OD",
)
axs1[1].set_xlabel("Cost function = exp", fontsize=10)
axs1[1].set_ylabel("$R^2$", fontsize=10)
axs1[1].set_xticks(x)
axs1[1].set_xticklabels(d_c_exp.index, fontsize=8)
axs1[1].legend(loc="upper left", fontsize=8, frameon=False)
axs1[1].set_ylim(0, 1.15)  # Set y-axis limits to range from 0 to 1
axs1[1].tick_params(axis="both", which="major", labelsize=8)

# Annotate bars with their R2 values
for i, (bar3, bar4) in enumerate(zip(bars3, bars4)):
    height3 = bar3.get_height()
    height4 = bar4.get_height()
    axs1[1].annotate(
        f"{height3:.2f}",
        xy=(bar3.get_x() + bar3.get_width() / 2, height3),
        xytext=(0, 3),
        textcoords="offset points",
        ha="center",
        fontsize=8,
    )
    axs1[1].annotate(
        f"{height4:.2f}",
        xy=(bar4.get_x() + bar4.get_width() / 2, height4),
        xytext=(0, 3),
        textcoords="offset points",
        ha="center",
        fontsize=8,
    )

# Adjust layout
# plt.tight_layout(rect=[0, 0, 1, 0.96])  # Leave space for the main title
# plt.show()
fig1.savefig("fig/fig4_model_comparison.png", bbox_inches="tight", dpi=300)
