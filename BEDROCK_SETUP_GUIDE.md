# AWS Bedrock Setup Guide

## Overview

The Agent Orchestrator supports **two AI providers**:
1. **Anthropic** - Direct Claude API (default)
2. **AWS Bedrock** - Claude via AWS Bedrock

The Bedrock integration uses the **Bedrock Converse API** (not the older InvokeModel API).

---

## Quick Answer to Your Questions

### 1. Uses Bedrock Converse API ✅

**Line 222 in `bedrock_reasoner.py`**:
```python
response = self.client.converse(
    modelId=self.model_id,
    messages=[...],
    inferenceConfig={...}
)
```

The orchestrator uses the **Bedrock Converse API**, which is the modern, recommended API for conversational interactions with foundation models in Bedrock.

### 2. Model ID (Not ARN)

Bedrock uses **Model IDs**, not ARNs. The format is:
```
anthropic.claude-{model}-{version}
```

**Examples**:
- `anthropic.claude-sonnet-3-5-v2-20241022` (Claude 3.5 Sonnet)
- `anthropic.claude-3-5-sonnet-20240620-v1:0` (Claude 3.5 Sonnet v1)
- `anthropic.claude-3-opus-20240229-v1:0` (Claude 3 Opus)
- `anthropic.claude-3-haiku-20240307-v1:0` (Claude 3 Haiku)

You specify this in the **config file**, not as an ARN.

---

## How to Switch from Anthropic to Bedrock

### Step 1: Update Configuration File

**File**: `config/orchestrator.yaml`

**Change line 17 from**:
```yaml
ai_provider: "anthropic"
```

**To**:
```yaml
ai_provider: "bedrock"
```

### Step 2: Configure Bedrock Settings

**Uncomment lines 27-43 in `config/orchestrator.yaml`**:

```yaml
orchestrator:
  name: "main-orchestrator"
  reasoning_mode: "hybrid"

  # Change this to use Bedrock
  ai_provider: "bedrock"

  # Bedrock Configuration
  bedrock:
    # AWS region where Bedrock is available
    region: "us-east-1"

    # Bedrock model ID (NOT an ARN!)
    model_id: "anthropic.claude-sonnet-3-5-v2-20241022"

    # Optional: IAM role ARN for cross-account access
    # Leave null to use default AWS credentials
    role_arn: null

    # Session name for STS assume role (only used if role_arn is set)
    session_name: "agent-orchestrator"

    # Optional: AWS profile from ~/.aws/credentials
    # Leave null to use default credentials
    aws_profile: null
```

### Step 3: Configure AWS Credentials

Choose ONE of these authentication methods:

#### Option A: Environment Variables (Recommended for Dev)
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-east-1
```

#### Option B: AWS Profile
```yaml
# In config/orchestrator.yaml
bedrock:
  aws_profile: "my-profile"  # Profile from ~/.aws/credentials
  region: "us-east-1"
  model_id: "anthropic.claude-sonnet-3-5-v2-20241022"
```

#### Option C: STS Assume Role (Cross-Account)
```yaml
# In config/orchestrator.yaml
bedrock:
  role_arn: "arn:aws:iam::123456789012:role/BedrockAccessRole"
  session_name: "agent-orchestrator"
  region: "us-east-1"
  model_id: "anthropic.claude-sonnet-3-5-v2-20241022"
```

#### Option D: EC2 Instance Role (Production)
```yaml
# In config/orchestrator.yaml
bedrock:
  region: "us-east-1"
  model_id: "anthropic.claude-sonnet-3-5-v2-20241022"
  # No credentials needed - uses instance role
```

### Step 4: Install AWS SDK
```bash
pip install boto3 botocore
```

### Step 5: Test the Configuration
```bash
python3 test_orchestrator_interactive.py
```

---

## Complete Configuration Examples

### Example 1: Basic Bedrock (Default Credentials)

```yaml
orchestrator:
  name: "main-orchestrator"
  reasoning_mode: "hybrid"
  ai_provider: "bedrock"

  bedrock:
    region: "us-east-1"
    model_id: "anthropic.claude-sonnet-3-5-v2-20241022"
```

**Uses**: Default AWS credentials from:
1. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
2. ~/.aws/credentials (default profile)
3. EC2 instance role

### Example 2: Bedrock with Specific Profile

```yaml
orchestrator:
  name: "main-orchestrator"
  reasoning_mode: "hybrid"
  ai_provider: "bedrock"

  bedrock:
    region: "us-west-2"
    model_id: "anthropic.claude-sonnet-3-5-v2-20241022"
    aws_profile: "production"  # From ~/.aws/credentials
```

### Example 3: Bedrock with Cross-Account Role

```yaml
orchestrator:
  name: "main-orchestrator"
  reasoning_mode: "hybrid"
  ai_provider: "bedrock"

  bedrock:
    region: "us-east-1"
    model_id: "anthropic.claude-sonnet-3-5-v2-20241022"
    role_arn: "arn:aws:iam::987654321098:role/OrchestrationRole"
    session_name: "prod-orchestrator-session"
```

---

## Available Bedrock Model IDs

### Claude 3.5 Models (Recommended)

| Model | Model ID | Best For |
|-------|----------|----------|
| **Claude 3.5 Sonnet v2** | `anthropic.claude-sonnet-3-5-v2-20241022` | Balanced performance & cost |
| Claude 3.5 Sonnet v1 | `anthropic.claude-3-5-sonnet-20240620-v1:0` | Previous version |

### Claude 3 Models

| Model | Model ID | Best For |
|-------|----------|----------|
| Claude 3 Opus | `anthropic.claude-3-opus-20240229-v1:0` | Complex reasoning (most expensive) |
| Claude 3 Sonnet | `anthropic.claude-3-sonnet-20240229-v1:0` | General purpose |
| Claude 3 Haiku | `anthropic.claude-3-haiku-20240307-v1:0` | Fast & cost-effective |

**Note**: Model availability varies by region. Check your AWS Bedrock console for enabled models.

---

## Model ID vs ARN

### ❌ Wrong (ARN Format)
```yaml
model_id: "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0"
```

### ✅ Correct (Model ID Format)
```yaml
model_id: "anthropic.claude-sonnet-3-5-v2-20241022"
```

**Why Model ID?**
- Bedrock Converse API uses model IDs, not ARNs
- ARNs are used for model management (permissions, listing)
- Model IDs are used for inference calls

---

## Bedrock Converse API Benefits

The orchestrator uses **Converse API** instead of the older InvokeModel API:

| Feature | Converse API | InvokeModel API |
|---------|--------------|-----------------|
| **Unified Interface** | ✅ Same for all models | ❌ Model-specific formats |
| **Message Format** | ✅ Standardized | ❌ Varies by model |
| **Multi-Turn** | ✅ Native support | ⚠️ Manual handling |
| **Tool Use** | ✅ Built-in | ⚠️ Model-specific |
| **Streaming** | ✅ Supported | ✅ Supported |
| **Future-Proof** | ✅ AWS recommended | ⚠️ Legacy |

**Code Location**: `agent_orchestrator/reasoning/bedrock_reasoner.py` line 222

---

## AWS Permissions Required

### Minimum IAM Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockInference",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": [
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-*"
      ]
    }
  ]
}
```

### If Using Assume Role (Cross-Account)

**Trust Policy** (on the target role):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::SOURCE_ACCOUNT:role/SourceRole"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**Permissions Policy** (on the target role):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "bedrock:InvokeModel",
      "Resource": "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-*"
    }
  ]
}
```

---

## Switching Between Providers

### Quick Switch Command

```bash
# Switch to Bedrock
sed -i '' 's/ai_provider: "anthropic"/ai_provider: "bedrock"/' config/orchestrator.yaml

# Switch back to Anthropic
sed -i '' 's/ai_provider: "bedrock"/ai_provider: "anthropic"/' config/orchestrator.yaml
```

### Environment-Specific Configs

**Development** (`config/orchestrator.yaml`):
```yaml
ai_provider: "anthropic"  # Use Anthropic API key
```

**Production** (`config/orchestrator.prod.yaml`):
```yaml
ai_provider: "bedrock"  # Use Bedrock with IAM role
bedrock:
  region: "us-east-1"
  model_id: "anthropic.claude-sonnet-3-5-v2-20241022"
```

Then specify config at runtime:
```bash
python3 test_orchestrator_interactive.py --config config/orchestrator.prod.yaml
```

---

## Validation Works with Both Providers

The **response validator** also supports Bedrock automatically:

**File**: `agent_orchestrator/validation/response_validator.py`

When `ai_provider: "bedrock"`, the validator uses the Bedrock client for AI-based validation.

---

## Cost Comparison

### Anthropic Direct API
- Pay per API call
- Billed by Anthropic
- Credit card required

### AWS Bedrock
- Pay per AWS account
- Billed by AWS (consolidated billing)
- Potential AWS credits/discounts
- Enterprise volume pricing

**Model Pricing** (Claude 3.5 Sonnet):
- Input: ~$3 per 1M tokens
- Output: ~$15 per 1M tokens
- (Same pricing for both Anthropic and Bedrock)

---

## Troubleshooting

### Error: "NoCredentialsError"

**Cause**: AWS credentials not configured

**Solution**:
```bash
# Option 1: Configure AWS CLI
aws configure

# Option 2: Set environment variables
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...

# Option 3: Use AWS profile
# Set aws_profile in config/orchestrator.yaml
```

### Error: "ValidationException: The provided model identifier is invalid"

**Cause**: Model ID is wrong or model not enabled

**Solution**:
1. Check available models in AWS Bedrock console
2. Enable model access in Bedrock settings
3. Verify region supports the model

### Error: "AccessDeniedException"

**Cause**: IAM permissions missing

**Solution**:
1. Add `bedrock:InvokeModel` permission
2. Verify resource ARN matches model
3. Check assume role trust policy (if using role_arn)

### Error: "ModelNotReadyException"

**Cause**: Model not enabled in your AWS account

**Solution**:
1. Go to AWS Bedrock console
2. Model access → Request model access
3. Enable Claude models
4. Wait for approval (usually instant)

---

## Testing Your Setup

### Test 1: Verify AWS Credentials
```bash
aws sts get-caller-identity
```

### Test 2: Test Bedrock Access
```bash
aws bedrock-runtime list-foundation-models --region us-east-1
```

### Test 3: Run Orchestrator
```bash
python3 test_orchestrator_interactive.py

You > calculate 25 + 75
```

**Check logs** for:
```
Bedrock reasoner initialized with model: anthropic.claude-sonnet-3-5-v2-20241022
Created Bedrock client with default credentials
```

---

## Summary

### To Switch to Bedrock:

1. **Edit `config/orchestrator.yaml`**:
   ```yaml
   ai_provider: "bedrock"
   bedrock:
     region: "us-east-1"
     model_id: "anthropic.claude-sonnet-3-5-v2-20241022"
   ```

2. **Configure AWS credentials** (choose one):
   - Environment variables
   - AWS profile
   - IAM role (EC2/ECS)
   - STS assume role

3. **Install boto3**:
   ```bash
   pip install boto3
   ```

4. **Test it**:
   ```bash
   python3 test_orchestrator_interactive.py
   ```

### Key Points:
- ✅ Uses **Bedrock Converse API** (modern API)
- ✅ Specify **Model ID** (not ARN)
- ✅ Same functionality as Anthropic
- ✅ Model ID format: `anthropic.claude-{model}-{version}`
- ✅ Default model: `anthropic.claude-sonnet-3-5-v2-20241022`

---

**Need Help?**
- AWS Bedrock Docs: https://docs.aws.amazon.com/bedrock/
- Model IDs: Check AWS Bedrock Console → Foundation Models
- Pricing: https://aws.amazon.com/bedrock/pricing/
