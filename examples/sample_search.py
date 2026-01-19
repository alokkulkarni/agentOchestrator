"""
Sample search tool for direct agent demonstration.

This module provides document search functionality that can be
called directly as an agent without MCP protocol.
"""

import asyncio
from typing import Any, Dict, List


# Mock document database
MOCK_DOCUMENTS = [
    {
        "id": "doc1",
        "title": "Introduction to Python",
        "content": "Python is a high-level programming language known for its simplicity and readability.",
        "tags": ["python", "programming", "tutorial"],
    },
    {
        "id": "doc2",
        "title": "Machine Learning Basics",
        "content": "Machine learning is a subset of AI that enables systems to learn from data.",
        "tags": ["ml", "ai", "data-science"],
    },
    {
        "id": "doc3",
        "title": "Web Development with FastAPI",
        "content": "FastAPI is a modern web framework for building APIs with Python.",
        "tags": ["python", "web", "api", "fastapi"],
    },
    {
        "id": "doc4",
        "title": "Agent Orchestration Patterns",
        "content": "Agent orchestration involves coordinating multiple agents to complete complex tasks.",
        "tags": ["agents", "orchestration", "architecture"],
    },
    {
        "id": "doc5",
        "title": "Async Programming in Python",
        "content": "Asyncio enables concurrent programming in Python using async/await syntax.",
        "tags": ["python", "async", "concurrency"],
    },
]


async def search_documents(
    query: str = "",
    keywords: List[str] = None,
    max_results: int = 10,
    min_relevance: float = 0.1,
) -> Dict[str, Any]:
    """
    Search through documents and return relevant results.

    This is an async function demonstrating async agent support.

    Args:
        query: Search query string (optional if keywords provided)
        keywords: List of keywords to search for (optional)
        max_results: Maximum number of results to return
        min_relevance: Minimum relevance score (0.0 to 1.0), default 0.1

    Returns:
        Dictionary with query, results, and metadata
    """
    # Simulate async processing
    await asyncio.sleep(0.1)

    # Build query terms from both query string and keywords list
    query_terms = set()

    if query:
        query_lower = query.lower()
        query_terms.update(query_lower.split())

    if keywords:
        query_terms.update(k.lower() for k in keywords)

    # If no query terms provided, return empty results
    if not query_terms:
        return {
            "query": query or "",
            "keywords": keywords or [],
            "results": [],
            "total_count": 0,
            "page": 1,
            "has_more": False,
        }

    results = []

    for doc in MOCK_DOCUMENTS:
        # Calculate simple relevance score
        relevance = _calculate_relevance(doc, query_terms)

        if relevance >= min_relevance:
            results.append({
                "id": doc["id"],
                "title": doc["title"],
                "content": doc["content"][:200] + "..." if len(doc["content"]) > 200 else doc["content"],
                "relevance": relevance,
                "metadata": {
                    "tags": doc["tags"],
                },
            })

    # Sort by relevance (highest first)
    results.sort(key=lambda x: x["relevance"], reverse=True)

    # Limit results
    results = results[:max_results]

    response = {
        "query": query or "",
        "results": results,
        "total_count": len(results),
        "page": 1,
        "has_more": False,
    }

    # Include keywords in response if provided
    if keywords:
        response["keywords"] = keywords

    return response


def _calculate_relevance(doc: Dict[str, Any], query_terms: set) -> float:
    """Calculate relevance score for a document."""
    score = 0.0

    # Check title matches (weight: 0.4)
    title_lower = doc["title"].lower()
    title_terms = set(title_lower.split())
    title_matches = len(query_terms & title_terms)
    if title_matches > 0:
        score += 0.4 * (title_matches / len(query_terms))

    # Check content matches (weight: 0.3)
    content_lower = doc["content"].lower()
    content_matches = sum(1 for term in query_terms if term in content_lower)
    if content_matches > 0:
        score += 0.3 * (content_matches / len(query_terms))

    # Check tag matches (weight: 0.3)
    tag_matches = sum(1 for term in query_terms if term in doc["tags"])
    if tag_matches > 0:
        score += 0.3 * (tag_matches / len(query_terms))

    return min(score, 1.0)


# Example usage
if __name__ == "__main__":
    async def test():
        result = await search_documents("python programming")
        print(f"Found {result['total_count']} results for '{result['query']}'")
        for r in result['results']:
            print(f"  - {r['title']} (relevance: {r['relevance']:.2f})")

    asyncio.run(test())
