import pandas as pd


def count(value):
    return 'n/a' if pd.isna(value) else f'{value:,.0f}'


def rate(value, decimals=0):
    return 'n/a' if pd.isna(value) else f'{value:.{decimals}%}'


def growth(value):
    return 'n/a' if pd.isna(value) else f'x{value:.2f}'


LABELS = {'rank': 'Rank', 'artist_name': 'Artist', 'exposure_score': 'Score',
          'new_listeners': 'New listeners', 'return_rate': 'Return rate',
          'eligible_new_listeners': 'Eligible n', 'repeat_listener_rate': 'Repeat rate',
          'growth_ratio': 'Growth', 'window_listeners': 'Listeners',
          'top_listener_share': 'Top-listener share', 'primary_artist_mbid': 'MBID'}


def display_table(frame):
    out = frame.copy()
    for col in out:
        if col in ('return_rate', 'repeat_listener_rate', 'top_listener_share', 'share_of_listens'):
            out[col] = out[col].map(rate)
        elif col == 'growth_ratio':
            out[col] = out[col].map(growth)
        elif col == 'exposure_score':
            out[col] = out[col].map(lambda x: 'n/a' if pd.isna(x) else f'{x:.1f}')
        elif col == 'primary_artist_mbid':
            out[col] = out[col].map(lambda x: 'yes' if pd.notna(x) and str(x).strip() else 'no')
        elif pd.api.types.is_numeric_dtype(out[col]):
            out[col] = out[col].map(count)
    return out.rename(columns=LABELS)
