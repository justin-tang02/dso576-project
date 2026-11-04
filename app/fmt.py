def count(value):
    if value is None:
        return "0"
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError, OverflowError):
        return "n/a"


def rate(value, digits=0):
    try:
        if value != value:
            return "n/a"
        return f"{float(value) * 100:.{digits}f}%"
    except (TypeError, ValueError):
        return "n/a"


def growth(value):
    try:
        return f"x{float(value):.2f}"
    except (TypeError, ValueError):
        return "n/a"


def score(value):
    try:
        return f"{float(value):.1f}"
    except (TypeError, ValueError):
        return "n/a"
