
from fastmcp import FastMCP
from typing import List, Dict, Any
import asyncio

# Create an MCP server
mcp = FastMCP("Search Server")

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
]

@mcp.tool()
async def search_documents(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Search through documents and return relevant results.
    """
    await asyncio.sleep(0.1)  # Simulate async work
    
    query_terms = set(query.lower().split())
    results = []

    for doc in MOCK_DOCUMENTS:
        doc_text = (doc["title"] + " " + doc["content"] + " ".join(doc["tags"])).lower()
        
        # Calculate relevance
        score = 0
        for term in query_terms:
            if term in doc_text:
                score += 1
                
        if score > 0:
            results.append({
                "title": doc["title"],
                "content": doc["content"],
                "score": score
            })
            
    # Sort by score
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:max_results]

if __name__ == "__main__":
    mcp.run()

if __name__ == "__main__":
    mcp.run(transport="stdio")
