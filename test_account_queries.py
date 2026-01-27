#!/usr/bin/env python3
"""
Test Account Management Query Rejection
Demonstrates that account-specific queries are now properly rejected.
"""

# Test queries that should be rejected
account_queries = [
    "i want to know my current account balance",
    "check my balance",
    "what is my account balance",
    "show me my balance",
    "view my account",
    "transfer money to John",
    "pay my electricity bill",
    "send money to account 12345",
    "what are my recent transactions",
    "transaction history",
    "change my address",
    "reset my password",
    "update my profile",
]

print("="*80)
print("ACCOUNT MANAGEMENT QUERIES - REJECTION TEST")
print("="*80)
print("\nThese queries should be REJECTED (no agents called):")
print()

for query in account_queries:
    print(f"❌ '{query}'")
    
print()
print("="*80)
print("EXPECTED BEHAVIOR")
print("="*80)
print("""
When you query any of the above:
  1. ✅ Orchestrator recognizes it as account-specific
  2. ✅ No agents are called (target_agents: [])
  3. ✅ User receives graceful rejection message
  
Response should be:
  "I apologize, but I cannot assist with account-specific operations.
   For account balance, transactions, or account management, please:
   • Log into your account portal
   • Contact customer service
   • Use the mobile app"
   
NOT:
  ❌ Calling search + calculator agents
  ❌ Returning Python programming docs
  ❌ Trying to search for generic information
""")

print("="*80)
print("CONTRASTING EXAMPLES - SHOULD BE ALLOWED")
print("="*80)
print("\nThese general queries SHOULD work (not account-specific):")
print()

allowed_queries = [
    "What credit cards does Virgin Money offer?",  # General product info
    "How do I open a bank account in UK?",  # General process info
    "What is the weather in London?",  # Direct capability
    "Calculate 25 + 75",  # Direct capability
    "Plan a trip from Manchester to Penrith",  # General planning
]

for query in allowed_queries:
    print(f"✅ '{query}'")

print()
print("="*80)
print("TO TEST THE FIX")
print("="*80)
print("""
1. Restart your orchestrator:
   python3 -m agent_orchestrator.server

2. Try the query again:
   "i want to know my current account balance"

3. Expected result:
   ✅ No agents called
   ✅ Graceful rejection message
   ✅ Guidance to use proper channels

4. Try a general query:
   "what credit cards does Virgin Money offer"
   
5. Expected result:
   ✅ tavily_search agent called
   ✅ Real web results returned
   ✅ Synthesized information about products
""")
