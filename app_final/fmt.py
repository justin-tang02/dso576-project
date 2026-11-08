"""Display formatting; exported CSVs retain raw values."""
import pandas as pd


def count(value):
    return "n/a" if pd.isna(value) else f"{value:,.0f}"


def rate(value, decimals=0):
    return "n/a" if pd.isna(value) else f"{value:.{decimals}%}"


def growth(value):
    return "n/a" if pd.isna(value) else f"x{value:.2f}"


def score(value):
    return "n/a" if pd.isna(value) else f"{value:.1f}"


def metric_table(rows):
    columns = {
        "artist_name": ("Artist", str), "window_listeners": ("Listeners", count),
        "new_listeners": ("New listeners", count), "return_rate": ("Return rate", rate),
        "eligible_new_listeners": ("Eligible n", count),
        "repeat_listener_rate": ("Repeat rate", rate), "growth_ratio": ("Growth", growth),
        "top_listener_share": ("Top-listener share", rate),
    }
    return pd.DataFrame({label: rows[key].map(fn) for key, (label, fn) in columns.items()})
