#!/usr/bin/env python3
"""
Quick test to verify search agent works with keywords parameter.
"""

import asyncio
import sys
sys.path.insert(0, '.')

from examples.sample_search import search_documents


async def test_search_with_keywords():
    """Test search with keywords parameter."""
    print("Testing search with keywords=['AI']...\n")

    result = await search_documents(
        query="search",
        keywords=["AI"],
        max_results=5
    )

    print(f"Query: {result['query']}")
    print(f"Keywords: {result.get('keywords', [])}")
    print(f"Total Results: {result['total_count']}")
    print(f"\nResults:")

    for i, r in enumerate(result['results'], 1):
        print(f"  {i}. {r['title']}")
        print(f"     Relevance: {r['relevance']:.2f}")
        print(f"     Tags: {r['metadata']['tags']}")
        print()

    if result['total_count'] == 0:
        print("❌ FAIL: No results returned for keywords=['AI']")
        return False
    else:
        print(f"✅ PASS: Found {result['total_count']} results for keywords=['AI']")
        return True


async def test_search_with_query_only():
    """Test search with query string only."""
    print("\n" + "="*70)
    print("Testing search with query='AI' only...\n")

    result = await search_documents(
        query="AI",
        max_results=5
    )

    print(f"Query: {result['query']}")
    print(f"Total Results: {result['total_count']}")
    print(f"\nResults:")

    for i, r in enumerate(result['results'], 1):
        print(f"  {i}. {r['title']}")
        print(f"     Relevance: {r['relevance']:.2f}")
        print()

    if result['total_count'] == 0:
        print("❌ FAIL: No results returned for query='AI'")
        return False
    else:
        print(f"✅ PASS: Found {result['total_count']} results for query='AI'")
        return True


async def test_search_with_both():
    """Test search with both query and keywords."""
    print("\n" + "="*70)
    print("Testing search with query='machine' and keywords=['learning']...\n")

    result = await search_documents(
        query="machine",
        keywords=["learning"],
        max_results=5
    )

    print(f"Query: {result['query']}")
    print(f"Keywords: {result.get('keywords', [])}")
    print(f"Total Results: {result['total_count']}")
    print(f"\nResults:")

    for i, r in enumerate(result['results'], 1):
        print(f"  {i}. {r['title']}")
        print(f"     Relevance: {r['relevance']:.2f}")
        print()

    if result['total_count'] == 0:
        print("❌ FAIL: No results returned")
        return False
    else:
        print(f"✅ PASS: Found {result['total_count']} results")
        return True


async def main():
    print("="*70)
    print("Search Agent Keyword Parameter Test")
    print("="*70 + "\n")

    test1 = await test_search_with_keywords()
    test2 = await test_search_with_query_only()
    test3 = await test_search_with_both()

    print("\n" + "="*70)
    print("Summary:")
    print(f"  Test 1 (keywords only): {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"  Test 2 (query only): {'✅ PASS' if test2 else '❌ FAIL'}")
    print(f"  Test 3 (both): {'✅ PASS' if test3 else '❌ FAIL'}")
    print("="*70 + "\n")

    if test1 and test2 and test3:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
