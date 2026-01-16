# Roles and Constraints Guide

This guide explains how to configure agent roles, constraints, and guardrails for secure and controlled agent execution.

## Table of Contents

1. [Overview](#overview)
2. [Agent Roles](#agent-roles)
3. [Agent Constraints](#agent-constraints)
4. [Guardrails](#guardrails)
5. [Examples](#examples)
6. [Best Practices](#best-practices)

## Overview

The Agent Orchestrator supports role-based access control (RBAC) and configurable constraints to ensure agents operate within defined boundaries. All configurations are defined in YAML files and enforced at runtime.

### Why Roles and Constraints?

- **Security**: Prevent unauthorized operations
- **Reliability**: Limit resource usage
- **Compliance**: Enforce business rules
- **Safety**: Protect against misuse
- **Auditability**: Track agent operations

## Agent Roles

Roles define what an agent is allowed to do and under what conditions.

### Role Configuration

```yaml
role:
  name: "role-name"              # Unique role identifier
  description: "Role purpose"    # What this role does
  allowed_operations:            # Operations this role can perform
    - "read"
    - "analyze"
  denied_operations:             # Explicitly blocked operations
    - "delete"
    - "modify"
  max_execution_time: 30         # Maximum seconds per execution
  max_input_size: 100000         # Maximum input size in bytes
  require_approval: false        # Whether human approval is needed
  guardrails:                    # Custom guardrails (key-value pairs)
    max_records: 1000
    allowed_formats: ["json", "csv"]
```

### Role Properties

#### `name` (required)
Unique identifier for the role. Use descriptive names that indicate the role's purpose.

**Examples**:
- `data-analyst` - Read-only data analysis
- `code-reviewer` - Code review and suggestions
- `content-generator` - Content creation
- `system-administrator` - Administrative operations

#### `description` (required)
Human-readable description of the role's purpose and capabilities.

#### `allowed_operations`
List of operations this role can perform. Use `["*"]` to allow all operations, or specify individual operations.

**Examples**:
```yaml
# Allow specific operations
allowed_operations:
  - "read"
  - "search"
  - "analyze"

# Allow all operations
allowed_operations:
  - "*"
```

#### `denied_operations`
Operations explicitly denied even if in `allowed_operations`. Useful for blocking dangerous operations.

**Examples**:
```yaml
denied_operations:
  - "delete"
  - "exec"
  - "eval"
  - "modify_system"
  - "shutdown"
```

#### `max_execution_time`
Maximum time in seconds an operation can run. Prevents long-running or hung operations.

**Recommendations**:
- Quick operations: 5-10 seconds
- Data processing: 30-60 seconds
- External API calls: 15-30 seconds
- Admin operations: 60-120 seconds

#### `max_input_size`
Maximum input size in bytes. Prevents large input attacks.

**Recommendations**:
- Simple queries: 10,000 bytes (10KB)
- Data processing: 1,000,000 bytes (1MB)
- File processing: 10,000,000 bytes (10MB)

#### `require_approval`
Whether operations require human approval before execution.

**Use cases**:
- Administrative operations
- Destructive operations
- High-cost operations
- Compliance-required operations

```yaml
require_approval: true  # Human must approve
require_approval: false # Auto-execute
```

#### `guardrails`
Custom guardrails as key-value pairs. Define role-specific constraints.

**Examples**:
```yaml
guardrails:
  # Data processing
  max_records: 10000
  max_field_size: 10000
  allow_nested_data: true
  max_nesting_depth: 5

  # API calls
  cache_results: true
  cache_ttl: 300
  max_retries: 3

  # Content generation
  max_tokens: 1000
  temperature: 0.7
  block_inappropriate: true

  # Security
  require_encryption: true
  pii_detection: true
  content_filter: true
```

## Agent Constraints

Constraints control how agents execute and interact with the system.

### Constraint Configuration

```yaml
constraints:
  max_retries: 3                 # Override default retry count
  timeout: 30                    # Override default timeout
  rate_limit: 60                 # Max calls per minute
  require_validation: false      # Require output validation
  allowed_input_fields:          # Allowed input fields
    - "query"
    - "parameters"
  denied_input_fields:           # Blocked input fields
    - "admin"
    - "password"
  output_sanitization: true      # Sanitize outputs
  log_level: "INFO"              # Logging level
```

### Constraint Properties

#### `max_retries`
Override default retry attempts for this agent.

```yaml
max_retries: 3  # Try up to 3 times
max_retries: 1  # No retries (admin operations)
max_retries: 5  # More retries for flaky operations
```

#### `timeout`
Override default timeout in seconds.

```yaml
timeout: 5   # Quick operations
timeout: 30  # Normal operations
timeout: 60  # Long operations
```

#### `rate_limit`
Maximum calls per minute. 0 for unlimited.

```yaml
rate_limit: 60  # 60 calls/minute
rate_limit: 10  # 10 calls/minute (external API)
rate_limit: 0   # Unlimited
```

#### `require_validation`
Whether output must pass validation before returning.

```yaml
require_validation: true   # Must validate
require_validation: false  # Optional validation
```

#### `allowed_input_fields`
Fields allowed in input. Use `["*"]` for all fields.

```yaml
# Allow specific fields
allowed_input_fields:
  - "query"
  - "parameters"
  - "data"

# Allow all fields
allowed_input_fields:
  - "*"
```

#### `denied_input_fields`
Fields explicitly denied in input. Overrides `allowed_input_fields`.

```yaml
denied_input_fields:
  - "admin"
  - "password"
  - "secret"
  - "api_key"
  - "token"
  - "command"
  - "script"
  - "code"
```

#### `output_sanitization`
Whether to sanitize outputs before returning.

```yaml
output_sanitization: true   # Always sanitize
output_sanitization: false  # No sanitization (trusted)
```

#### `log_level`
Logging level for this agent.

```yaml
log_level: "DEBUG"    # Verbose logging
log_level: "INFO"     # Normal logging
log_level: "WARNING"  # Warnings only
log_level: "ERROR"    # Errors only
```

## Guardrails

Guardrails are custom constraints specific to an agent's role or domain.

### Common Guardrails

#### Data Processing
```yaml
guardrails:
  max_records: 10000           # Max records to process
  max_field_size: 10000        # Max bytes per field
  allow_nested_data: true      # Allow nested structures
  max_nesting_depth: 5         # Max nesting levels
  allowed_formats: ["json", "csv"]
```

#### External APIs
```yaml
guardrails:
  cache_results: true          # Enable caching
  cache_ttl: 300              # Cache for 5 minutes
  max_retries: 3              # API retry count
  require_valid_location: true # Validate inputs
  allowed_domains: ["api.example.com"]
```

#### Content Generation
```yaml
guardrails:
  max_tokens: 1000            # Max output tokens
  temperature: 0.7            # Creativity level
  block_inappropriate: true   # Content filter
  require_citation: true      # Require sources
  plagiarism_check: true     # Check for plagiarism
```

#### Security & Compliance
```yaml
guardrails:
  require_encryption: true    # Encrypt sensitive data
  pii_detection: true        # Detect PII
  content_filter: true       # Filter content
  audit_log: true           # Log all operations
  require_justification: true # Require reason
  allowed_users: ["admin"]   # Restrict to users
```

## Examples

### Example 1: Safe Calculator
```yaml
- name: "calculator"
  type: "direct"
  direct_tool:
    module: "examples.sample_calculator"
    function: "calculate"

  role:
    name: "math-processor"
    description: "Safe mathematical calculations"
    allowed_operations: ["add", "subtract", "multiply", "divide"]
    denied_operations: ["exec", "eval"]
    max_execution_time: 5
    max_input_size: 10000
    require_approval: false
    guardrails:
      max_operands: 100
      allow_division_by_zero: false

  constraints:
    max_retries: 2
    timeout: 5
    rate_limit: 60
    allowed_input_fields: ["operation", "operands"]
    denied_input_fields: ["code", "script"]
```

### Example 2: Data Analyst (Read-Only)
```yaml
- name: "data_analyst"
  type: "direct"

  role:
    name: "data-analyst"
    description: "Read-only data analysis and reporting"
    allowed_operations: ["read", "analyze", "aggregate"]
    denied_operations: ["write", "delete", "modify"]
    max_execution_time: 60
    max_input_size: 5000000  # 5MB
    require_approval: false
    guardrails:
      read_only: true
      max_records: 100000
      export_formats: ["json", "csv", "pdf"]

  constraints:
    require_validation: true
    output_sanitization: true
    log_level: "INFO"
```

### Example 3: Admin Agent (High Privilege)
```yaml
- name: "admin_agent"
  type: "direct"

  role:
    name: "system-administrator"
    description: "Administrative operations with approval"
    allowed_operations: ["read", "analyze", "configure"]
    denied_operations: ["delete_all", "shutdown", "restart"]
    max_execution_time: 120
    max_input_size: 10000
    require_approval: true  # REQUIRES APPROVAL
    guardrails:
      require_audit_log: true
      require_justification: true
      allowed_users: ["admin", "supervisor"]
      multi_factor_auth: true

  constraints:
    max_retries: 1  # No auto-retry
    timeout: 120
    rate_limit: 5   # Very limited
    require_validation: true
    output_sanitization: true
    log_level: "WARNING"  # Log everything
```

### Example 4: External API Agent
```yaml
- name: "weather_api"
  type: "mcp"
  connection:
    url: "https://api.weather.com"

  role:
    name: "weather-provider"
    description: "Weather data via external API"
    allowed_operations: ["get_weather", "get_forecast"]
    denied_operations: ["set_weather", "delete"]
    max_execution_time: 15
    max_input_size: 5000
    require_approval: false
    guardrails:
      cache_results: true
      cache_ttl: 300
      require_valid_location: true
      allowed_countries: ["US", "CA", "UK"]

  constraints:
    max_retries: 3
    timeout: 15
    rate_limit: 10  # Respect API limits
    denied_input_fields: ["api_key", "credentials"]
```

## Best Practices

### 1. Principle of Least Privilege
Grant agents only the permissions they need.

```yaml
# ❌ BAD: Too permissive
allowed_operations: ["*"]
denied_operations: []

# ✅ GOOD: Specific permissions
allowed_operations: ["read", "search"]
denied_operations: ["delete", "modify", "exec"]
```

### 2. Defense in Depth
Use multiple layers of protection.

```yaml
# Multiple safeguards
role:
  denied_operations: ["delete"]  # Block at role level
  guardrails:
    read_only: true              # Enforce read-only

constraints:
  denied_input_fields: ["admin"] # Block dangerous inputs
  output_sanitization: true      # Sanitize outputs
```

### 3. Appropriate Timeouts
Set realistic timeouts based on operation type.

```yaml
# Quick operations
max_execution_time: 5
timeout: 5

# Data processing
max_execution_time: 30
timeout: 30

# External APIs
max_execution_time: 15
timeout: 15
```

### 4. Rate Limiting
Protect against abuse and respect limits.

```yaml
# Internal operations
rate_limit: 60  # 60/minute

# External APIs
rate_limit: 10  # Respect vendor limits

# Admin operations
rate_limit: 5   # Very limited
```

### 5. Input Validation
Explicitly deny dangerous inputs.

```yaml
denied_input_fields:
  - "password"
  - "secret"
  - "api_key"
  - "token"
  - "command"
  - "script"
  - "code"
  - "exec"
  - "eval"
  - "admin"
  - "root"
```

### 6. Human Approval for Sensitive Operations
Require approval for high-risk operations.

```yaml
role:
  require_approval: true  # For admin, delete, modify
  guardrails:
    require_justification: true
    require_audit_log: true
```

### 7. Logging and Auditing
Log appropriately based on risk.

```yaml
# Normal operations
log_level: "INFO"

# Sensitive operations
log_level: "WARNING"

# Debugging
log_level: "DEBUG"
```

### 8. Regular Review
Periodically review and update roles and constraints:

- Review access logs
- Update constraints based on usage patterns
- Remove unused permissions
- Tighten guardrails as needed
- Document changes

## Testing Roles and Constraints

Test your configurations:

```bash
# Validate configuration
python3 -c "from agent_orchestrator.config import load_agents_config; load_agents_config('config/agents.yaml')"

# Test specific agent
python3 example_usage.py

# Run tests
pytest tests/
```

## Troubleshooting

### Operation Denied
```
Error: Operation 'delete' denied by role
```
**Solution**: Check `denied_operations` in role configuration

### Input Field Blocked
```
Error: Input field 'admin' not allowed
```
**Solution**: Check `denied_input_fields` in constraints

### Rate Limit Exceeded
```
Error: Rate limit exceeded (10 calls/minute)
```
**Solution**: Wait or increase `rate_limit` in constraints

### Timeout
```
Error: Operation timed out after 5s
```
**Solution**: Increase `max_execution_time` or `timeout`

### Approval Required
```
Info: Operation requires human approval
```
**Solution**: Set `require_approval: false` or implement approval workflow

## Summary

Roles and constraints provide:

- ✅ **Security**: Block dangerous operations
- ✅ **Control**: Limit resource usage
- ✅ **Compliance**: Enforce policies
- ✅ **Flexibility**: Configure per agent
- ✅ **Auditability**: Track all operations

Use the examples in `config/agents.yaml` as templates for your own agents.
