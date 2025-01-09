from tavily import AsyncTavilyClient
import asyncio
from langsmith import traceable


tavily_async_client = AsyncTavilyClient()

@traceable(name="tavily_search_async")
async def tavily_search_async(search_queries):
    """Performs concurrent web searches using the Tavily API."""
    search_tasks = []
    for query in search_queries:
        query_str = query.search_query
        # Wrap individual search in a traceable function
        search_tasks.append(_single_tavily_search(query_str))
    return await asyncio.gather(*search_tasks)

@traceable(name="single_tavily_search")
async def _single_tavily_search(query_str):
    """Performs a single web search using the Tavily API."""
    return await tavily_async_client.search(query_str, max_results=5, include_raw_content=True)
