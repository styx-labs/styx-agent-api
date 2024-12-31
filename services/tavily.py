from tavily import AsyncTavilyClient
import asyncio
from langsmith import traceable

tavily_async_client = AsyncTavilyClient()


@traceable
async def tavily_search_async(search_queries):
    """Performs concurrent web searches using the Tavily API."""
    search_tasks = []
    for query in search_queries:
        query_str = query.search_query
        search_tasks.append(
            tavily_async_client.search(
                query_str, max_results=10, include_raw_content=True, depth="advanced"
            )
        )
    return await asyncio.gather(*search_tasks)


@traceable
async def tavily_extract_async(urls):
    """Extracts content from URLs using Tavily's Extract API.

    Args:
        urls: A single URL string or list of URLs (max 20 per batch)

    Returns:
        dict: Extract API response with results and any failed URLs
    """
    if isinstance(urls, str):
        urls = [urls]

    try:
        return await tavily_async_client.extract(urls=urls)
    except Exception as e:
        print(f"Error in Tavily extract: {e}")
        raise
