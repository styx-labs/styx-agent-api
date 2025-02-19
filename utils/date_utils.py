from datetime import date


def convert_date_dict(date_dict: dict) -> date | None:
    """Convert a date dictionary from Proxycurl API to a Python date object."""
    if not date_dict or not all(k in date_dict for k in ["year", "month", "day"]):
        return None
    return date(year=date_dict["year"], month=date_dict["month"], day=date_dict["day"])
