# Tech Insights Agent - AI-Powered Configuration

## Overview

The Tech Insights agent is now AI-powered, using the model gateway to generate and validate software engineering trends on-demand. It includes comprehensive guardrails, validation, and fallback mechanisms.

## Architecture

```
User Query → Orchestrator → Tech Insights Agent
                                    ↓
                        1. Check AI Mode (env: TECH_INSIGHTS_USE_AI)
                                    ↓
                        ┌──────────┴───────────┐
                        │                      │
                    AI Mode                Curated Mode
                        │                      │
                        ↓                      ↓
            2. Call Model Gateway      2. Return Static Data
               (Generate 20 insights)         ↓
                        ↓                 4. Validate
            3. Parse JSON Response            ↓
                        ↓                 5. Format & Return
            4. Validate Output
               (Guardrails Check)
                        ↓
               Valid? ──No──→ Fallback to Curated
                │
               Yes
                ↓
            5. Format & Return
```

## Key Features

### 1. **AI-Powered Generation**
- Generates insights via model gateway at `http://localhost:8585/v1/generate`
- Uses temperature 0.7 for balanced creativity and factuality
- Generates 20 comprehensive insights in one call
- Includes specific examples, tools, frameworks, and metrics

### 2. **Comprehensive Validation**
Validates every AI-generated insight against:

**Structural Validation:**
- Required fields: rank, title, category, technical, non_technical, impact, adoption
- Valid categories: ai, languages, tools, ml
- Valid impact levels: low, medium, high, very high
- Valid adoption stages: early, growing, steady, widespread

**Content Quality:**
- Technical perspective: 100-800 characters
- Non-technical perspective: 50-600 characters
- All required categories must be represented
- Minimum 10 insights, maximum 20 insights

**Quality Score:**
- Each insight scored 0.0-1.0
- Overall quality score must be ≥ 0.8
- Falls back to curated insights if quality is low

### 3. **Guardrails**

Defined in `config/agents.yaml`:

```yaml
guardrails:
  # Content guardrails
  min_insights: 10
  max_insights: 20
  required_categories: ["ai", "languages", "tools", "ml"]
  required_fields: ["rank", "title", "category", "technical", "non_technical", "impact", "adoption"]

  # Quality guardrails
  min_technical_length: 100
  max_technical_length: 800
  min_non_technical_length: 50
  max_non_technical_length: 600

  # Validation guardrails
  validate_before_response: true
  min_quality_score: 0.8
  fallback_on_validation_failure: true

  # Content quality
  require_specific_examples: true
  require_factual_data: true
  no_speculation: true
  include_both_perspectives: true
```

### 4. **Constraints**

```yaml
constraints:
  max_retries: 2
  timeout: 60  # AI calls need more time
  rate_limit: 10  # Lower rate limit due to AI costs
  require_validation: true  # MUST validate AI output
  allowed_input_fields:
    - "category"
    - "audience"
    - "query"
    - "refresh"  # Allow AI refresh
    - "gateway_url"
  denied_input_fields:
    - "admin"
    - "override"
    - "bypass_validation"
```

### 5. **Fallback Strategy**

**Automatic Fallback Triggers:**
1. Model gateway is unreachable
2. AI response parsing fails
3. Validation fails (quality score < 0.8)
4. Timeout (> 60 seconds)
5. Any exception during AI generation

**Fallback Behavior:**
- Automatically switches to curated (static) insights
- No error shown to user
- Maintains same response format
- Logs fallback reason

## Usage

### Mode 1: Curated Insights (Default)

Returns pre-validated, curated insights:

```bash
# Via environment variable (default)
export TECH_INSIGHTS_USE_AI=false

# Or via orchestrator
curl -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "show me tech insights"}'
```

**Response includes:**
- 20 curated insights
- Validation status: ✅ Valid
- Quality score: 100%
- Source: "Tech Insights Agent (Curated)"

### Mode 2: AI-Generated Insights

Generates fresh insights via AI:

```bash
# Enable AI mode
export TECH_INSIGHTS_USE_AI=true

# Request with refresh=true
curl -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "generate fresh tech insights",
    "refresh": true
  }'
```

**Response includes:**
- 20 AI-generated insights (if validation passes)
- Validation status and quality score
- Source: "Tech Insights Agent (AI-powered)"
- Validation details (issues, categories covered)

### Filtering Options

**By Category:**
```bash
# AI trends only
curl -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "show me AI trends",
    "category": "ai"
  }'
```

**By Audience:**
```bash
# Technical perspective only
curl -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "show me tech insights for engineers",
    "audience": "technical"
  }'

# Non-technical perspective only
curl -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "show me tech insights for business",
    "audience": "non-technical"
  }'
```

## Configuration

### Environment Variables

```bash
# Enable/disable AI mode (default: true)
TECH_INSIGHTS_USE_AI=true

# Model gateway URL (default: http://localhost:8585)
MODEL_GATEWAY_URL=http://localhost:8585
```

### Agent Configuration

Located in `config/agents.yaml`:

```yaml
- name: "tech_insights"
  type: "direct"
  enabled: true  # Enable/disable agent

  constraints:
    timeout: 60  # Timeout for AI generation
    rate_limit: 10  # Requests per minute
    require_validation: true  # Always validate
```

## Validation Details

### Validation Response

```json
{
  "validation": {
    "status": true,  // Overall validation pass/fail
    "quality_score": 0.95,  // 0.0-1.0
    "issues": [  // List of validation issues
      "Insight #3: Technical perspective too short",
      "Missing required categories: {'ml'}"
    ]
  }
}
```

### Quality Score Calculation

- **1.0**: Perfect insight (all checks pass)
- **0.5**: Insight has issues but is usable
- **0.0**: Critical issues (missing fields, invalid category)

**Overall Score** = Average of all insight scores

**Threshold** = 0.8 (80%)

## Model Gateway Integration

### Request Format

```json
{
  "messages": [
    {
      "role": "user",
      "content": "You are a technology trends analyst. Generate the top 20 software engineering trends..."
    }
  ],
  "temperature": 0.7,
  "max_tokens": 4000
}
```

### Response Format

```json
{
  "content": "{\"insights\": [{\"rank\": 1, \"title\": \"...\", ...}]}",
  "model": "claude-sonnet-4-5",
  "provider": "anthropic",
  "usage": {
    "input_tokens": 150,
    "output_tokens": 3500
  }
}
```

## Monitoring & Observability

### Metrics to Track

1. **AI Generation Success Rate**
   - Successful generations vs. fallbacks
   - Track via metadata field: `ai_generated: true/false`

2. **Validation Quality**
   - Average quality score over time
   - Common validation issues

3. **Performance**
   - Average response time (AI vs curated)
   - Gateway timeout rate

4. **Cost**
   - Token usage per request
   - Daily/monthly AI call volume

### Logging

Agent logs include:
- AI generation attempts
- Validation results
- Fallback triggers
- Quality scores
- Execution time

Check logs:
```bash
tail -f /tmp/orchestrator.log | grep tech_insights
```

## Testing

### 1. Test Curated Mode (No AI)

```bash
python3 examples/sample_tech_insights.py
```

Expected output:
```
✅ Retrieved 20 insights
Source: Tech Insights Agent (Curated)
Validation: ✅ Valid
Quality Score: 100.00%
```

### 2. Test AI Mode

```bash
# Ensure gateway is running
curl http://localhost:8585/health

# Enable AI mode
export TECH_INSIGHTS_USE_AI=true

# Test with refresh
python3 -c "
from examples.sample_tech_insights import get_tech_insights
result = get_tech_insights(refresh=True)
print(f'AI Generated: {result[\"metadata\"][\"ai_generated\"]}')
print(f'Quality Score: {result[\"validation\"][\"quality_score\"]:.2%}')
print(f'Insights: {result[\"total_insights\"]}')
"
```

### 3. Test via Orchestrator

```bash
# Test query routing
curl -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "show me top 20 tech insights"}'
```

## Troubleshooting

### Issue: AI mode not activating

**Solution:**
```bash
# Check environment variable
echo $TECH_INSIGHTS_USE_AI

# Set explicitly
export TECH_INSIGHTS_USE_AI=true
```

### Issue: All requests falling back to curated

**Possible causes:**
1. Model gateway not running
2. Gateway timeout (> 60s)
3. Validation failing consistently

**Debug:**
```bash
# Check gateway health
curl http://localhost:8585/health

# Check orchestrator logs
tail -50 /tmp/orchestrator.log | grep -A5 "tech_insights"
```

### Issue: Low quality scores

**Causes:**
- AI generating insights that are too short/long
- Missing required categories
- Invalid field values

**Solution:**
- Adjust guardrails in `config/agents.yaml`
- Update prompt in `examples/sample_tech_insights.py` line 112
- Check model gateway model selection

## Best Practices

1. **Use Curated Mode for Production**
   - Faster response times
   - Predictable content
   - Zero AI costs

2. **Use AI Mode for Research**
   - On-demand updates
   - Fresh perspectives
   - Custom category requests

3. **Monitor Quality Scores**
   - Track validation issues
   - Adjust guardrails as needed
   - Set alerts for low scores

4. **Rate Limiting**
   - AI mode: 10 requests/minute
   - Curated mode: 30 requests/minute
   - Prevents excessive AI costs

5. **Fallback Strategy**
   - Always have curated insights as fallback
   - Never show validation errors to end users
   - Log all fallback events for analysis

## Future Enhancements

1. **Caching**
   - Cache AI-generated insights for 24 hours
   - Reduce model gateway calls
   - Faster responses for repeat queries

2. **Incremental Updates**
   - Update specific categories only
   - Preserve high-quality insights
   - Replace only outdated content

3. **Multi-Model Support**
   - Try multiple models if one fails
   - Compare quality across models
   - Select best output

4. **User Feedback Loop**
   - Collect user ratings
   - Adjust quality thresholds
   - Improve prompts based on feedback

---

**Last Updated:** 2026-01-21
**Agent Version:** 2026.1
**Status:** ✅ Production Ready
