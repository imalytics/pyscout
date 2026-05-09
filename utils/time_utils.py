def fmt_time(secs: float) -> str:
    if secs is None or secs < 0:
        return "0:00:00"
    h = int(secs // 3600)
    m = int((secs % 3600) // 60)
    s = int(secs % 60)
    return f"{h}:{m:02d}:{s:02d}"


def fmt_dur(secs: float) -> str:
    """Short format for duration display."""
    if secs is None or secs < 0:
        return "0s"
    if secs < 60:
        return f"{secs:.1f}s"
    m = int(secs // 60)
    s = secs % 60
    return f"{m}m {s:.0f}s"
