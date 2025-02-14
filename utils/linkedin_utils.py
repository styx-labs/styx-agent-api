import re


def extract_linkedin_id(url: str) -> str | None:
    """Extract the LinkedIn public identifier from a profile URL."""
    try:
        # Remove any query parameters
        url = url.split("?")[0]
        # Remove trailing slash if present
        url = url.rstrip("/")
        # Get the last part of the URL which should be the ID
        match = re.search(r"linkedin\.com/in/([^/]+)", url)
        return match.group(1) if match else None
    except Exception:
        return None
