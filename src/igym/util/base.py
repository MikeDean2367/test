from datetime import datetime, timedelta
import re

def parse_duration(duration_str: str) -> timedelta:
    """Parse duration string like '1d2h30m15s' into timedelta"""
    if not duration_str:
        return None
    
    pattern = r'((?P<days>\d+)d)?((?P<hours>\d+)h)?((?P<minutes>\d+)m)?((?P<seconds>\d+)s)?'
    match = re.fullmatch(pattern, duration_str)
    if not match:
        raise ValueError(f"Invalid duration format: {duration_str}")
    
    parts = match.groupdict()
    time_params = {}
    for name, param in parts.items():
        if param:
            time_params[name] = int(param)
    
    return timedelta(**time_params)

