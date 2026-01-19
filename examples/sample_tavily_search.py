"""
Tavily Search Agent

AI-powered search API designed for LLMs and AI agents.
Provides real-time, accurate search results with source citations.

Features:
- Real-time web search
- AI-powered result ranking
- Source citations
- Configurable depth (basic/advanced)
- Domain filtering
- Date filtering

API: https://tavily.com
"""

import asyncio
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

# Tavily SDK
try:
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None


def get_tavily_search(
    query: str,
    search_depth: str = "basic",
    max_results: int = 5,
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
    include_answer: bool = True,
    include_raw_content: bool = False,
    include_images: bool = False,
) -> Dict[str, Any]:
    """
    Perform Tavily search (synchronous wrapper).

    Args:
        query: Search query
        search_depth: "basic" or "advanced" (advanced = more comprehensive)
        max_results: Maximum number of results (1-20)
        include_domains: List of domains to include (e.g., ["github.com"])
        exclude_domains: List of domains to exclude
        include_answer: Include AI-generated answer summary
        include_raw_content: Include raw page content
        include_images: Include relevant images

    Returns:
        Dictionary with search results
    """
    # Run async function in event loop
    return asyncio.run(
        tavily_search(
            query=query,
            search_depth=search_depth,
            max_results=max_results,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            include_answer=include_answer,
            include_raw_content=include_raw_content,
            include_images=include_images,
        )
    )


async def tavily_search(
    query: str,
    search_depth: str = "basic",
    max_results: int = 5,
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
    include_answer: bool = True,
    include_raw_content: bool = False,
    include_images: bool = False,
) -> Dict[str, Any]:
    """
    Perform Tavily search using their API.

    Tavily is an AI-powered search engine optimized for AI agents and LLMs.
    It provides accurate, real-time search results with citations.

    Args:
        query: Search query string
        search_depth: Search depth - "basic" (faster) or "advanced" (comprehensive)
        max_results: Maximum number of results to return (1-20)
        include_domains: Optional list of domains to search within
        exclude_domains: Optional list of domains to exclude
        include_answer: Include AI-generated summary answer
        include_raw_content: Include full page content in results
        include_images: Include relevant images in results

    Returns:
        Dictionary containing:
        - success: bool - Whether the search succeeded
        - query: str - The search query
        - results: List[Dict] - Search results with title, url, content, score
        - answer: str - AI-generated answer (if include_answer=True)
        - images: List[Dict] - Relevant images (if include_images=True)
        - total_results: int - Number of results returned
        - search_depth: str - Depth used for search
        - timestamp: str - When the search was performed

    Example:
        >>> result = await tavily_search("Python async programming", max_results=3)
        >>> print(result['answer'])
        >>> for r in result['results']:
        ...     print(f"{r['title']}: {r['url']}")
    """
    # Check if Tavily is installed
    if TavilyClient is None:
        return {
            "success": False,
            "error": "Tavily SDK not installed. Install with: pip install tavily-python",
            "query": query,
            "results": [],
            "total_results": 0,
        }

    # Get API key from environment
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return {
            "success": False,
            "error": "TAVILY_API_KEY not found in environment variables",
            "query": query,
            "results": [],
            "total_results": 0,
            "hint": "Set TAVILY_API_KEY in your .env file or environment",
        }

    try:
        # Initialize Tavily client
        client = TavilyClient(api_key=api_key)

        # Validate parameters
        max_results = max(1, min(max_results, 20))  # Clamp to 1-20
        if search_depth not in ["basic", "advanced"]:
            search_depth = "basic"

        # Perform search
        search_params = {
            "query": query,
            "search_depth": search_depth,
            "max_results": max_results,
            "include_answer": include_answer,
            "include_raw_content": include_raw_content,
            "include_images": include_images,
        }

        # Add domain filters if provided
        if include_domains:
            search_params["include_domains"] = include_domains
        if exclude_domains:
            search_params["exclude_domains"] = exclude_domains

        # Execute search
        response = client.search(**search_params)

        # Format results
        results = []
        for result in response.get("results", []):
            results.append({
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "content": result.get("content", ""),
                "score": result.get("score", 0.0),
                "raw_content": result.get("raw_content", "") if include_raw_content else None,
            })

        # Build response
        output = {
            "success": True,
            "query": query,
            "results": results,
            "total_results": len(results),
            "search_depth": search_depth,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Add answer if included
        if include_answer and "answer" in response:
            output["answer"] = response["answer"]

        # Add images if included
        if include_images and "images" in response:
            output["images"] = response["images"]

        # Add metadata
        output["metadata"] = {
            "api": "tavily",
            "version": "1.0",
            "depth": search_depth,
            "filters": {
                "include_domains": include_domains,
                "exclude_domains": exclude_domains,
            },
        }

        return output

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "query": query,
            "results": [],
            "total_results": 0,
            "timestamp": datetime.utcnow().isoformat(),
        }


# Examples and test function
async def test_tavily_search():
    """Test the Tavily search agent."""
    print("=" * 70)
    print("TAVILY SEARCH AGENT TEST")
    print("=" * 70)

    # Test 1: Basic search
    print("\n" + "-" * 70)
    print("Test 1: Basic Search")
    print("-" * 70)

    result = await tavily_search(
        query="Claude AI by Anthropic",
        search_depth="basic",
        max_results=3,
        include_answer=True,
    )

    print(f"\nSuccess: {result['success']}")
    if result['success']:
        print(f"Query: {result['query']}")
        print(f"Total Results: {result['total_results']}")

        if 'answer' in result:
            print(f"\n📝 AI Answer:")
            print(f"   {result['answer'][:200]}...")

        print(f"\n🔍 Search Results:")
        for i, r in enumerate(result['results'], 1):
            print(f"\n   {i}. {r['title']}")
            print(f"      URL: {r['url']}")
            print(f"      Score: {r['score']:.3f}")
            print(f"      Content: {r['content'][:150]}...")
    else:
        print(f"Error: {result.get('error')}")

    # Test 2: Advanced search with domain filter
    print("\n" + "-" * 70)
    print("Test 2: Advanced Search with Domain Filter")
    print("-" * 70)

    result = await tavily_search(
        query="Python asyncio tutorial",
        search_depth="advanced",
        max_results=5,
        include_domains=["python.org", "realpython.com"],
        include_answer=True,
    )

    print(f"\nSuccess: {result['success']}")
    if result['success']:
        print(f"Query: {result['query']}")
        print(f"Total Results: {result['total_results']}")
        print(f"Search Depth: {result['search_depth']}")

        print(f"\n🔍 Results:")
        for i, r in enumerate(result['results'], 1):
            print(f"   {i}. {r['title'][:60]}...")
            print(f"      {r['url']}")
    else:
        print(f"Error: {result.get('error')}")

    # Test 3: Search with images
    print("\n" + "-" * 70)
    print("Test 3: Search with Images")
    print("-" * 70)

    result = await tavily_search(
        query="Python logo",
        max_results=2,
        include_answer=False,
        include_images=True,
    )

    print(f"\nSuccess: {result['success']}")
    if result['success']:
        print(f"Query: {result['query']}")
        print(f"Total Results: {result['total_results']}")

        if 'images' in result:
            print(f"\n🖼️  Images Found: {len(result['images'])}")
            for i, img in enumerate(result['images'][:3], 1):
                print(f"   {i}. {img.get('url', 'N/A')[:80]}")
    else:
        print(f"Error: {result.get('error')}")

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_tavily_search())
