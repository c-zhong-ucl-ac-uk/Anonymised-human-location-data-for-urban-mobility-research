import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams


from matplotlib.colors import LinearSegmentedColormap

# =============================================================================
# Stylizing matplotlib
# =============================================================================
# FONT
rcParams["font.family"] = "sans-serif"  # sans-serif
rcParams["font.sans-serif"] = ["Helvetica"]
rcParams["legend.fontsize"] = "small"  # medium
rcParams["font.size"] = 7  # 10 default

# TICK
rcParams["xtick.labelsize"] = "small"  # medium
rcParams["ytick.labelsize"] = "small"  # medium
rcParams["xtick.major.width"] = 2 / 3.0  # 0.8
rcParams["ytick.major.width"] = 2 / 3.0
rcParams["xtick.minor.width"] = 2 / 3.0  # 0.6
rcParams["ytick.minor.width"] = 2 / 3.0
rcParams["xtick.major.size"] = 3  # 3.5
rcParams["ytick.major.size"] = 3
rcParams["xtick.minor.size"] = 1.5  # 2
rcParams["ytick.minor.size"] = 1.5
rcParams["xtick.major.pad"] = "2.3"  # 3.5
rcParams["ytick.major.pad"] = "2.3"
rcParams["xtick.minor.pad"] = "2.3"  # 3.5
rcParams["ytick.minor.pad"] = "2.3"
rcParams["ytick.direction"] = "in"  # out
rcParams["xtick.direction"] = "in"
rcParams["xtick.top"] = False
rcParams["ytick.right"] = False

# axes
rcParams["axes.spines.top"] = False
rcParams["axes.spines.right"] = False
rcParams["axes.linewidth"] = 2 / 3.0  # 0.8
rcParams["axes.labelpad"] = 2  # 4
rcParams["lines.linewidth"] = 1  # 1.5
rcParams["mathtext.default"] = "regular"
# rcParams['axes.labelsize'] = 'small'  # medium
# rcParams['figure.labelsize'] = 'small'  # medium

# EXPORT
rcParams["figure.dpi"] = 300  # 100
rcParams["svg.fonttype"] = "none"

# COLORS
# colors = ["#1980E6", "#FF9123","#61C2FF" ]
# colors = ["#D55E00", "#FF9123","#61C2FF",'#07AB92','#014C4C', '#FF7DBE']
colors = [
    "#37469D",
    "#477DBA",
    "#B5E0EF",
    "#FBE395",
    "#FBAE60",
    "#EE5B39",
    "#D52C26",
]
colormap = "RdYlBu"

cm = 1 / 2.54  # centimeters in inches


def shuffle_colormap(cmap_name, n_colors=10, random_state=42):
    """
    Create a shuffled version of a given colormap

    Parameters:
    -----------
    cmap_name : str
        Name of the original colormap
    n_colors : int
        Number of colors to sample
    random_state : int
        Random seed for reproducibility

    Returns:
    --------
    matplotlib.colors.LinearSegmentedColormap
        A new colormap with shuffled colors
    """
    # Set random seed
    np.random.seed(random_state)

    # Get original colormap
    original_cmap = plt.get_cmap(cmap_name)

    # Sample colors from original colormap
    # colors = original_cmap(np.logspace(-0.5, 0, n_colors))
    colors = original_cmap(np.linspace(0, 1, n_colors))

    # Shuffle the colors
    np.random.shuffle(colors)

    # Create new colormap
    shuffled_cmap = LinearSegmentedColormap.from_list(f"shuffled_{cmap_name}", colors)

    return shuffled_cmap
