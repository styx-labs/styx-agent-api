from datetime import date
from typing import Optional, Dict


def convert_date_dict(date_dict: Optional[Dict]) -> Optional[date]:
    """Convert a date dictionary from Proxycurl API to a Python date object."""
    if not date_dict or not all(k in date_dict for k in ["year", "month", "day"]):
        return None
    return date(year=date_dict["year"], month=date_dict["month"], day=date_dict["day"])
