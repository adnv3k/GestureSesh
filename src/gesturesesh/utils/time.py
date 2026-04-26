"""Time formatting helpers."""


def format_seconds(sec):
    """
    Convert *sec* seconds (float or int, >= 0) to a zero-padded
    ``HH:MM:SS`` string. If *sec* has a fraction, show milliseconds:
    ``HH:MM:SS.mmm``.

    Examples
    --------
    >>> format_seconds(3661)
    '01:01:01'
    >>> format_seconds(5.3)
    '00:00:05.300'
    >>> format_seconds(0.007)
    '00:00:00.007'
    """
    if sec < 0:
        raise ValueError("seconds cannot be negative")

    hours, remainder = divmod(sec, 3600)
    minutes, sec_fraction = divmod(remainder, 60)

    hours = int(hours)
    minutes = int(minutes)

    int_secs = int(sec_fraction)
    millis_raw = int(round((sec_fraction - int_secs) * 1000))

    if millis_raw == 1000:
        millis_raw = 0
        int_secs += 1
        if int_secs == 60:
            int_secs = 0
            minutes += 1
            if minutes == 60:
                minutes = 0
                hours += 1

    if millis_raw == 0:
        secs_str = f"{int_secs:02d}"
    else:
        secs_str = f"{int_secs:02d}.{millis_raw:03d}"

    return f"{hours:02d}:{minutes:02d}:{secs_str}"
