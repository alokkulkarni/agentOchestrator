#!/usr/bin/env python3
"""
Intent Classification Test
Demonstrates how the AI reasoner distinguishes between personal account queries
and general information queries, especially for financial products.
"""

print("="*80)
print("INTELLIGENT INTENT CLASSIFICATION")
print("="*80)
print("\nThe AI reasoner now classifies queries based on INTENT, not just keywords.\n")

print("="*80)
print("KEY: Possessive Indicators")
print("="*80)
print("""
Possessive pronouns indicate PERSONAL account queries:
  • "my", "mine", "I", "me", "our"
  
Combined with financial terms:
  • balance, transaction, account, card, loan, mortgage, payment

= Personal Account Query → REJECT (AGENTS: none)
""")

print("="*80)
print("TEST CASES: Credit Cards")
print("="*80)

test_cases = [
    {
        "query": "What is MY credit card balance?",
        "contains_possessive": True,
        "intent": "Personal account query",
        "expected": "AGENTS: none",
        "reason": "Contains 'MY' + 'balance' = Account-specific"
    },
    {
        "query": "Show me MY credit card transactions",
        "contains_possessive": True,
        "intent": "Personal account query",
        "expected": "AGENTS: none",
        "reason": "Contains 'ME/MY' + 'transactions' = Account-specific"
    },
    {
        "query": "What credit cards does Virgin Money offer?",
        "contains_possessive": False,
        "intent": "General product information",
        "expected": "AGENTS: tavily_search",
        "reason": "No possessive, asking about products = General info"
    },
    {
        "query": "Compare credit card interest rates",
        "contains_possessive": False,
        "intent": "General information",
        "expected": "AGENTS: tavily_search",
        "reason": "No possessive, general comparison = General info"
    },
    {
        "query": "How do I apply for a credit card?",
        "contains_possessive": False,
        "intent": "General process information",
        "expected": "AGENTS: tavily_search",
        "reason": "'I' here means 'anyone', not possessive = General info"
    },
]

for i, test in enumerate(test_cases, 1):
    possessive_mark = "🔴" if test["contains_possessive"] else "🟢"
    print(f"\n{i}. Query: \"{test['query']}\"")
    print(f"   {possessive_mark} Possessive: {'YES' if test['contains_possessive'] else 'NO'}")
    print(f"   🎯 Intent: {test['intent']}")
    print(f"   ✅ Expected: {test['expected']}")
    print(f"   💡 Reason: {test['reason']}")

print("\n" + "="*80)
print("TEST CASES: Other Financial Products")
print("="*80)

financial_tests = [
    ("MY loan status", "AGENTS: none", "Personal loan query"),
    ("Mortgage rates in UK", "AGENTS: tavily_search", "General rates info"),
    ("MY mortgage payment due date", "AGENTS: none", "Personal payment query"),
    ("What savings accounts are available?", "AGENTS: tavily_search", "General products"),
    ("MY savings account balance", "AGENTS: none", "Personal balance query"),
    ("Investment options for retirement", "AGENTS: tavily_search", "General advice"),
    ("MY investment portfolio", "AGENTS: none", "Personal portfolio query"),
]

for query, expected, intent in financial_tests:
    has_possessive = any(word in query.lower() for word in ['my ', 'mine', ' i ', 'me '])
    mark = "🔴" if has_possessive else "🟢"
    print(f"\n{mark} \"{query}\"")
    print(f"   → {expected} ({intent})")

print("\n" + "="*80)
print("AI REASONING LOGIC")
print("="*80)
print("""
Step 1: Check for possessive indicators
  - Look for: "my", "mine", "I", "me", "our"
  
Step 2: Check for financial terms
  - Look for: balance, transaction, account, card, loan, mortgage
  
Step 3: Classify intent
  - Possessive + Financial = Personal Account Query → AGENTS: none
  - No Possessive + Financial = General Information → AGENTS: tavily_search
  
Step 4: Even if specific pattern not in rules.yaml
  - AI uses intelligence to classify correctly
  - Notes in reasoning: "Classified as account-specific based on intent"
  
Step 5: Log missing patterns (future enhancement)
  - "SUGGESTION: Add pattern 'my savings account' to rules.yaml"
  - Helps improve rules over time
""")

print("="*80)
print("BENEFITS OF INTENT CLASSIFICATION")
print("="*80)
print("""
✅ Doesn't require exhaustive rules for every variation
✅ Handles new financial products automatically
✅ Understands context and intent, not just keywords
✅ Distinguishes "my credit card" from "credit cards"
✅ More intelligent than simple pattern matching
✅ Can suggest missing rules for improvement

Example:
  Query: "what is my crypto wallet balance"
  - Even if "crypto wallet" not in rules
  - AI detects: "my" + "balance" = Personal query
  - Decision: AGENTS: none
  - Note: "Consider adding 'crypto wallet balance' to rules"
""")

print("="*80)
print("TO TEST THE ENHANCED SYSTEM")
print("="*80)
print("""
1. Restart orchestrator:
   python3 -m agent_orchestrator.server

2. Test personal queries (should be rejected):
   • "what is my credit card balance"
   • "show me my loan status"
   • "my mortgage payment"

3. Test general queries (should work):
   • "what credit cards does Virgin Money offer"
   • "compare mortgage rates"
   • "credit card interest rates"

4. Verify reasoning:
   Check logs to see AI's intent classification
   Should mention "personal account query" or "possessive indicator"
""")

print("="*80)
print("✅ INTELLIGENT INTENT CLASSIFICATION READY")
print("="*80)
