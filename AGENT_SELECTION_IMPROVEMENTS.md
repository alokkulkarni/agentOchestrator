# Agent Selection Improvements for Planning Agent

## Issue Summary

**Problem**: The planning agent was being incorrectly selected for customer service queries like "i want to change my address" when it should only be used for software development planning.

**Root Cause**: The AI reasoning system (hybrid reasoner with gateway) was overriding agent selection and suggesting the planning agent even though:
1. No customer service/profile management agent exists
2. Planning agent capabilities should be restricted to software planning only

## Changes Made

### 1. Restricted Planning Agent Capabilities ([config/agents.yaml](config/agents.yaml))

**Before**:
```yaml
capabilities:
  - "planning"
  - "requirements"
  - "user-stories"
  - "epics"
  - "project-planning"
  - "application-design"
  - "product-management"
```

**After**:
```yaml
capabilities:
  - "project-planning"
  - "application-planning"
  - "requirements-planning"
  - "epic-creation"
  - "user-story-creation"
  - "software-planning"
  - "product-planning"
```

**Description Update**:
```yaml
description: "Creates detailed SOFTWARE APPLICATION plans with epics and user stories. ONLY for software/app development planning, NOT for personal tasks, business operations, or customer service."
```

**Impact**: Removes generic "planning" keyword and emphasizes software-specific planning keywords only.

### 2. Enhanced AI Reasoner Prompt ([agent_orchestrator/reasoning/gateway_reasoner.py](agent_orchestrator/reasoning/gateway_reasoner.py))

Added critical agent selection rules:

```python
CRITICAL AGENT SELECTION RULES:
1. ONLY select agents whose capabilities DIRECTLY match the query intent
2. Planning agent: ONLY for software/application development planning with explicit keywords:
   - "plan", "design app", "create application", "build software", "develop system"
   - Example queries that SHOULD use planning: "plan a web app", "design system architecture"
   - Example queries that SHOULD NOT use planning: "change my address", "update profile", "help me with X"
3. If query is about customer service, personal information, account updates, address changes:
   - Return AGENTS: none (no agent available for this query)
4. If NO agent capabilities match the query, MUST respond with: AGENTS: none
5. When uncertain, it's better to return "none" than select the wrong agent
6. Do NOT try to be helpful by selecting loosely related agents - be strict about capability matching
```

**Impact**: Provides explicit guidance on when NOT to use planning agent and when to return "none".

### 3. Added "none" Response Handling

Updated parsing logic to handle when AI reasoner determines no suitable agent exists:

```python
# Check if response is "none" - meaning no suitable agent found
if agents_line.lower() == "none":
    logger.info("AI reasoner determined no suitable agent for query")
    return None
```

**Impact**: Allows AI to explicitly say "no agent matches" which orchestrator handles gracefully.

### 4. Added Agent Role Descriptions to Prompt

Modified prompt building to include role descriptions:

```python
for idx, agent in enumerate(agent_capabilities, 1):
    name = agent.name
    capabilities = agent.capabilities
    role_desc = agent.role.get("description", "") if hasattr(agent, "role") and agent.role else ""
    prompt += f"{idx}. {name}: {', '.join(capabilities)}"
    if role_desc:
        prompt += f" - {role_desc}"
    prompt += "\n"
```

**Impact**: Provides AI with more context about agent purpose, not just capability keywords.

### 5. Fixed session_id Bug ([agent_orchestrator/orchestrator.py](agent_orchestrator/orchestrator.py))

Fixed uninitialized variable error:

```python
# Before (line 653)
user_id = input_data.get("user_id", session_id or "anonymous")

# After
session_id = get_session_id()
user_id = input_data.get("user_id", session_id or "anonymous")
```

**Impact**: Prevents crash when evaluating actions.

## Current Status

### ✅ FIXED - All Changes Implemented Successfully

**Test Results**:

1. **Address Change Query** ✅ WORKING
   ```bash
   Query: "i want to change my address"
   Result: "No agents could be determined for this request"
   Agents Selected: []
   ```
   
2. **Software Planning Query** ✅ WORKING
   ```bash
   Query: "plan a web application for task management"
   Result: Planning agent selected and asks relevant questions
   Agents Selected: ['planning', 'tech_insights', 'data_processor']
   ```

### Changes Implemented

#### 1. **Disabled Low-Confidence AI Override** ([agent_orchestrator/reasoning/hybrid_reasoner.py](agent_orchestrator/reasoning/hybrid_reasoner.py))

Added confidence threshold check (0.5) before allowing AI override:

```python
ai_confidence = validation.get("confidence", 0)

# Only use AI override if confidence is reasonable (>= 0.5)
if ai_confidence < 0.5:
    logger.info(
        f"AI override confidence too low ({ai_confidence:.2f}), "
        f"returning no match instead of incorrect suggestion"
    )
    return None
```

**Impact**: When AI suggests agents with low confidence (< 0.5), the system now returns `None` (no match) instead of using the incorrect suggestion. This prevents the planning agent from being selected for non-planning queries.

#### 2. **Applied Fix to Both Override Paths**
- Multi-agent selection override (line ~302)
- Single-agent selection override (line ~372)

Both paths now check confidence before allowing override.

### ✅ Completed
- Planning agent capabilities restricted to software planning only
- AI reasoner prompt enhanced with explicit rules
- "none" response handling implemented
- Bug fix for session_id variable
- Agent role descriptions added to AI context
- **Hybrid reasoner confidence threshold implemented** ✅ NEW
- **AI override disabled for low confidence (< 0.5)** ✅ NEW

### ⚠️ Previously Blocked (NOW FIXED)
~~The hybrid reasoner's AI override mechanism still triggers~~ **FIXED by implementing confidence threshold**

## Implementation Summary

The issue was successfully resolved by implementing **Option 1 (Recommended)** - disabling AI override when confidence is low. This prevents the system from making incorrect agent suggestions when it's uncertain, resulting in clean "no agent available" responses for unsupported queries while maintaining correct agent selection for supported use cases.

## Recommended Next Steps

### ✅ No Further Action Required for Planning Agent Selection

The planning agent selection issue has been fully resolved. Future enhancements (optional):

### Option 3: Create Customer Service Agent (FUTURE ENHANCEMENT)
Add a customer service agent that handles profile/account queries:

```yaml
- name: "customer_service"
  capabilities:
    - "account-management"
    - "profile-updates"
    - "address-change"
    - "customer-support"
  role:
    description: "Handles customer account and profile management requests"
```

**Pros**: Actually handles the user's intent
**Cons**: Requires implementing the agent logic
**Status**: Optional - system now correctly reports "no agent available" for these queries

## Testing

### Test Case: Address Change Query
```bash
curl -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "i want to change my address", "user_id": "test_user"}'
```

**Expected Behavior**: 
- Return error: "No agents could be determined for this request"
- Conversational wrapper adds: "I don't have a customer service agent to help with address changes"

**Current Behavior**:
- Selects: search, data_processor, planning (via AI override)
- Planning agent asks clarification questions thinking it's a software planning request

### Test Case: Software Planning (Should Still Work)
```bash
curl -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "plan a web application for managing tasks", "user_id": "test_user"}'
```

**Expected Behavior**:
- Correctly selects planning agent
- Asks relevant questions about the web application

## Files Modified

1. **config/agents.yaml** - Planning agent capabilities and description
2. **agent_orchestrator/reasoning/gateway_reasoner.py** - AI reasoner prompt and parsing
3. **agent_orchestrator/orchestrator.py** - session_id bug fix

## Related Documentation

- [EVALUATORS_GUIDE.md](EVALUATORS_GUIDE.md) - Policy enforcement system
- [AGENT_SELECTION_EXPLAINED.md](AGENT_SELECTION_EXPLAINED.md) - Agent selection flow
- [MULTI_AGENT_CONFIRMATION.md](MULTI_AGENT_CONFIRMATION.md) - Multi-agent workflows

---

*Date: January 27, 2026*
*Status: Partial - Requires hybrid reasoner override logic update*
