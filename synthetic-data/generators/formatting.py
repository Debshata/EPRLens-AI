"""Indian number / date formatting helpers shared by fixtures and (later) PDF rendering."""
from datetime import date


def inr(x: float, decimals: int = 2) -> str:
    """Indian digit grouping: 1234567.8 → '12,34,567.80'."""
    neg = x < 0
    s = f"{abs(x):.{decimals}f}"
    whole, _, frac = s.partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups) + "," + tail
    out = whole + ("." + frac if frac else "")
    return ("-" if neg else "") + out


def date_dmy(d: date, style: str = "slash") -> str:
    if style == "slash":
        return d.strftime("%d/%m/%Y")
    if style == "dash":
        return d.strftime("%d-%m-%Y")
    if style == "mon":
        return d.strftime("%d-%b-%Y")
    return d.isoformat()
