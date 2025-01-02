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
        search_tasks.append(tavily_async_client.search(query_str, max_results=10))
    return await asyncio.gather(*search_tasks)
