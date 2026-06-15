"""
Matplotlib plotting helpers for the reinforcement learning notebooks.

Kept here so the notebook cells stay short and readable. Matplotlib only, to
match the rest of the project. Colours follow the palette used elsewhere in the
repository (steelblue for the rule-based baseline, green/orange for the two
learned update rules).
"""

import matplotlib.pyplot as plt

BASELINE_COLOUR = "#4682b4"      # steelblue
Q_LEARNING_COLOUR = "#2ca02c"    # green
SARSA_COLOUR = "#ff7f0e"         # orange
TD_ERROR_COLOUR = "#d62728"      # red
STATES_COLOUR = "#9467bd"        # purple

UPDATE_RULE_COLOUR = {
    "q_learning": Q_LEARNING_COLOUR,
    "sarsa": SARSA_COLOUR,
}
UPDATE_RULE_LABEL = {
    "q_learning": "Q-learning",
    "sarsa": "SARSA",
}

ABLATION_COLOUR = {
    "mission_only": "#2ca02c",       # green
    "participant_only": "#ff7f0e",   # orange
    "joint": "#9467bd",              # purple
}
ABLATION_LABEL = {
    "mission_only": "mission only",
    "participant_only": "participant only",
    "joint": "joint",
}


def plot_training_curves(curves_by_label, baseline_win_rate = None, title = None):
    """
    Plot win-rate, mean absolute TD error, and visited-state count against
    training episode for one or more runs.

    curves_by_label: dict label -> curves dict with keys checkpoint_episodes,
        win_rate_curve, td_error_curve, and a states curve (mission or participant).
    """
    figure, axes = plt.subplots(1, 3, figsize = (15, 4))

    for label, curves in curves_by_label.items():
        episodes = curves["checkpoint_episodes"]
        colour = UPDATE_RULE_COLOUR.get(label, None)
        axes[0].plot(episodes, curves["win_rate_curve"], label = UPDATE_RULE_LABEL.get(label, label), color = colour)
        axes[1].plot(episodes, curves["td_error_curve"], label = UPDATE_RULE_LABEL.get(label, label), color = colour)
        states_curve = curves["mission_states_curve"] if any(curves["mission_states_curve"]) else curves["participant_states_curve"]
        axes[2].plot(episodes, states_curve, label = UPDATE_RULE_LABEL.get(label, label), color = colour)

    if baseline_win_rate is not None:
        axes[0].axhline(baseline_win_rate, linestyle = "--", color = BASELINE_COLOUR, alpha = 0.8, label = "baseline")

    axes[0].set_title("Training win rate")
    axes[0].set_xlabel("episode")
    axes[0].set_ylabel("win rate (training block)")
    axes[0].legend()

    axes[1].set_title("Mean absolute TD error")
    axes[1].set_xlabel("episode")
    axes[1].set_ylabel("mean |TD error|")
    axes[1].legend()

    axes[2].set_title("Distinct states visited")
    axes[2].set_xlabel("episode")
    axes[2].set_ylabel("states in Q-table")
    axes[2].legend()

    if title:
        figure.suptitle(title)
    figure.tight_layout()
    return figure


def _interval_error_bars(point, interval):
    """Asymmetric (lower, upper) error-bar distances from a Wilson interval dict."""
    return [point - interval["lower"], interval["upper"] - point]


def plot_ablation_comparison(summaries, player_counts, ablations, title = None):
    """
    Grouped bar chart by player count: a rule-based baseline bar plus one learned
    bar per ablation (mission-only, participant-only, joint), each with Wilson 95%
    confidence-interval error bars.

    summaries: dict keyed by (ablation, player_count) -> evaluation summary dict.
        The baseline win rate is identical across ablations, so it is read once
        per player count from the first ablation's summary.
    """
    series_names = ["baseline"] + list(ablations)
    series_count = len(series_names)
    bar_width = 0.8 / series_count
    positions = list(range(len(player_counts)))

    figure, axis = plt.subplots(figsize = (10, 5.5))
    every_rate = []
    for series_index, series_name in enumerate(series_names):
        rates = []
        lower_errors = []
        upper_errors = []
        for player_count in player_counts:
            reference_summary = summaries[(ablations[0], player_count)]
            if series_name == "baseline":
                rate = reference_summary["baseline_win_rate"]
                interval = reference_summary["baseline_win_interval"]
            else:
                summary = summaries[(series_name, player_count)]
                rate = summary["rl_win_rate"]
                interval = summary["rl_win_interval"]
            lower_error, upper_error = _interval_error_bars(rate, interval)
            rates.append(rate)
            lower_errors.append(lower_error)
            upper_errors.append(upper_error)
            every_rate.append(rate)

        offset = (series_index - (series_count - 1) / 2) * bar_width
        colour = BASELINE_COLOUR if series_name == "baseline" else ABLATION_COLOUR.get(series_name)
        label = "rule-based baseline" if series_name == "baseline" else ABLATION_LABEL.get(series_name, series_name)
        axis.bar(
            [position + offset for position in positions], rates, bar_width,
            yerr = [lower_errors, upper_errors], capsize = 3, color = colour, label = label,
        )

    axis.set_xticks(positions)
    axis.set_xticklabels([f"{player_count} players" for player_count in player_counts])
    axis.set_ylabel("win rate")
    axis.set_ylim(0, max(every_rate) * 1.25)
    axis.legend(ncol = 2)
    if title:
        axis.set_title(title)
    figure.tight_layout()
    return figure


def plot_policy_heatmap(grid, row_labels, column_labels, title = None, value_labels = None, colour_map = "viridis"):
    """
    Render a 2D grid of integer/float policy values as a heatmap with cell annotations.

    grid: 2D list (rows x columns) of numeric values.
    value_labels: optional dict mapping a cell value to a short text label for annotation.
    """
    figure, axis = plt.subplots(figsize = (1.2 * len(column_labels) + 2, 0.6 * len(row_labels) + 2))
    image = axis.imshow(grid, aspect = "auto", cmap = colour_map)

    axis.set_xticks(range(len(column_labels)))
    axis.set_xticklabels(column_labels, rotation = 30, ha = "right")
    axis.set_yticks(range(len(row_labels)))
    axis.set_yticklabels(row_labels)

    for row_index, row in enumerate(grid):
        for column_index, value in enumerate(row):
            text = value_labels.get(value, str(value)) if value_labels else f"{value:.2f}"
            axis.text(column_index, row_index, text, ha = "center", va = "center", color = "white", fontsize = 9)

    if title:
        axis.set_title(title)
    figure.colorbar(image, ax = axis)
    figure.tight_layout()
    return figure
