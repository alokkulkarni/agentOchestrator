"""
Cost tracking for Agent Orchestrator AI reasoner calls.

Tracks costs for:
- Anthropic API calls (reasoning)
- AWS Bedrock calls (reasoning)
- Gateway calls (reasoning via gateway)
"""

from typing import Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ReasonerPricing:
    """Pricing information for AI reasoner models."""

    input_price_per_1m: float
    output_price_per_1m: float
    provider: str
    model_name: str


class OrchestratorCostTracker:
    """Tracks costs for orchestrator AI reasoner calls."""

    def __init__(self):
        """Initialize cost tracker with pricing data."""
        # Anthropic pricing (January 2025)
        self.pricing_data: Dict[str, ReasonerPricing] = {
            # Claude Sonnet 4.5
            "claude-sonnet-4-5-20250929": ReasonerPricing(
                input_price_per_1m=3.00,
                output_price_per_1m=15.00,
                provider="anthropic",
                model_name="Claude Sonnet 4.5",
            ),
            # Claude Opus 4.5
            "claude-opus-4-5-20251101": ReasonerPricing(
                input_price_per_1m=15.00,
                output_price_per_1m=75.00,
                provider="anthropic",
                model_name="Claude Opus 4.5",
            ),
            # Claude 3.5 Sonnet
            "claude-3-5-sonnet-20241022": ReasonerPricing(
                input_price_per_1m=3.00,
                output_price_per_1m=15.00,
                provider="anthropic",
                model_name="Claude 3.5 Sonnet",
            ),
            "claude-3-5-sonnet-20240620": ReasonerPricing(
                input_price_per_1m=3.00,
                output_price_per_1m=15.00,
                provider="anthropic",
                model_name="Claude 3.5 Sonnet",
            ),
            # Bedrock models
            "anthropic.claude-sonnet-3-5-v2-20241022": ReasonerPricing(
                input_price_per_1m=3.00,
                output_price_per_1m=15.00,
                provider="bedrock",
                model_name="Claude 3.5 Sonnet (Bedrock)",
            ),
            "anthropic.claude-3-5-sonnet-20240620-v1:0": ReasonerPricing(
                input_price_per_1m=3.00,
                output_price_per_1m=15.00,
                provider="bedrock",
                model_name="Claude 3.5 Sonnet (Bedrock)",
            ),
        }

        # Default pricing for unknown models
        self.default_pricing = ReasonerPricing(
            input_price_per_1m=3.00,
            output_price_per_1m=15.00,
            provider="unknown",
            model_name="Unknown Model",
        )

        # Cost tracking accumulators
        self.total_cost_usd = 0.0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.reasoning_calls = 0
        self.cost_by_provider: Dict[str, float] = {}
        self.cost_by_model: Dict[str, float] = {}

    def calculate_cost(
        self, model: str, input_tokens: int, output_tokens: int, provider: Optional[str] = None
    ) -> Tuple[float, ReasonerPricing]:
        """
        Calculate cost for a reasoning call.

        Args:
            model: Model identifier
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            provider: Optional provider override

        Returns:
            Tuple of (cost_usd, pricing_info)
        """
        # Get pricing info
        pricing = self.get_pricing(model, provider)

        # Calculate costs
        input_cost = (input_tokens / 1_000_000) * pricing.input_price_per_1m
        output_cost = (output_tokens / 1_000_000) * pricing.output_price_per_1m
        total_cost = input_cost + output_cost

        return total_cost, pricing

    def track_reasoning_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        provider: Optional[str] = None,
    ) -> Dict[str, any]:
        """
        Calculate and track cost for a reasoning call.

        Args:
            model: Model identifier
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            provider: Optional provider name

        Returns:
            Dictionary with cost breakdown
        """
        cost_usd, pricing = self.calculate_cost(model, input_tokens, output_tokens, provider)

        # Update accumulators
        self.total_cost_usd += cost_usd
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.reasoning_calls += 1

        # Track by provider
        provider_name = provider or pricing.provider
        if provider_name not in self.cost_by_provider:
            self.cost_by_provider[provider_name] = 0.0
        self.cost_by_provider[provider_name] += cost_usd

        # Track by model
        if model not in self.cost_by_model:
            self.cost_by_model[model] = 0.0
        self.cost_by_model[model] += cost_usd

        return {
            "cost_usd": round(cost_usd, 6),
            "input_cost_usd": round(
                (input_tokens / 1_000_000) * pricing.input_price_per_1m, 6
            ),
            "output_cost_usd": round(
                (output_tokens / 1_000_000) * pricing.output_price_per_1m, 6
            ),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "model": pricing.model_name,
            "provider": pricing.provider,
        }

    def get_pricing(self, model: str, provider: Optional[str] = None) -> ReasonerPricing:
        """
        Get pricing information for a model.

        Args:
            model: Model identifier
            provider: Optional provider name

        Returns:
            ReasonerPricing object
        """
        # Try exact match
        if model in self.pricing_data:
            return self.pricing_data[model]

        # Use default pricing
        return self.default_pricing

    def get_total_cost(self) -> float:
        """Get total accumulated cost in USD."""
        return round(self.total_cost_usd, 2)

    def get_cost_by_provider(self) -> Dict[str, float]:
        """Get cost breakdown by provider."""
        return {provider: round(cost, 2) for provider, cost in self.cost_by_provider.items()}

    def get_cost_by_model(self) -> Dict[str, float]:
        """Get cost breakdown by model."""
        return {model: round(cost, 2) for model, cost in self.cost_by_model.items()}

    def get_statistics(self) -> Dict[str, any]:
        """
        Get cost tracking statistics.

        Returns:
            Dictionary with statistics
        """
        avg_cost = (
            self.total_cost_usd / self.reasoning_calls if self.reasoning_calls > 0 else 0
        )

        return {
            "total_reasoning_cost_usd": round(self.total_cost_usd, 2),
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "reasoning_calls": self.reasoning_calls,
            "average_cost_per_call": round(avg_cost, 6),
            "cost_by_provider": self.get_cost_by_provider(),
            "cost_by_model": self.get_cost_by_model(),
        }

    def reset_statistics(self):
        """Reset cost tracking statistics."""
        self.total_cost_usd = 0.0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.reasoning_calls = 0
        self.cost_by_provider = {}
        self.cost_by_model = {}


# Global cost tracker instance
orchestrator_cost_tracker = OrchestratorCostTracker()
