"""
Cost tracking for Model Gateway requests.

Calculates costs based on:
- Provider-specific pricing
- Model-specific pricing
- Input/output token counts
- Batch discounts (if applicable)
"""

from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class PricingTier(Enum):
    """Pricing tiers for different models."""

    FLAGSHIP = "flagship"  # Most expensive (Opus, GPT-4)
    STANDARD = "standard"  # Mid-tier (Sonnet, GPT-3.5-turbo)
    FAST = "fast"  # Cheaper (Haiku, Claude Instant)


@dataclass
class ModelPricing:
    """Pricing information for a model."""

    input_price_per_1m: float  # Price per 1M input tokens
    output_price_per_1m: float  # Price per 1M output tokens
    tier: PricingTier
    provider: str
    model_name: str


class CostTracker:
    """Tracks and calculates costs for API requests."""

    def __init__(self):
        """Initialize cost tracker with pricing data."""
        # Anthropic pricing (as of January 2025)
        # Source: https://www.anthropic.com/pricing
        self.pricing_data: Dict[str, ModelPricing] = {
            # Claude Sonnet 4.5
            "claude-sonnet-4-5-20250929": ModelPricing(
                input_price_per_1m=3.00,
                output_price_per_1m=15.00,
                tier=PricingTier.STANDARD,
                provider="anthropic",
                model_name="Claude Sonnet 4.5",
            ),
            # Claude Opus 4.5
            "claude-opus-4-5-20251101": ModelPricing(
                input_price_per_1m=15.00,
                output_price_per_1m=75.00,
                tier=PricingTier.FLAGSHIP,
                provider="anthropic",
                model_name="Claude Opus 4.5",
            ),
            # Claude 3.5 Sonnet
            "claude-3-5-sonnet-20241022": ModelPricing(
                input_price_per_1m=3.00,
                output_price_per_1m=15.00,
                tier=PricingTier.STANDARD,
                provider="anthropic",
                model_name="Claude 3.5 Sonnet",
            ),
            "claude-3-5-sonnet-20240620": ModelPricing(
                input_price_per_1m=3.00,
                output_price_per_1m=15.00,
                tier=PricingTier.STANDARD,
                provider="anthropic",
                model_name="Claude 3.5 Sonnet",
            ),
            # Claude 3 Opus
            "claude-3-opus-20240229": ModelPricing(
                input_price_per_1m=15.00,
                output_price_per_1m=75.00,
                tier=PricingTier.FLAGSHIP,
                provider="anthropic",
                model_name="Claude 3 Opus",
            ),
            # Claude 3 Sonnet
            "claude-3-sonnet-20240229": ModelPricing(
                input_price_per_1m=3.00,
                output_price_per_1m=15.00,
                tier=PricingTier.STANDARD,
                provider="anthropic",
                model_name="Claude 3 Sonnet",
            ),
            # Claude 3 Haiku
            "claude-3-haiku-20240307": ModelPricing(
                input_price_per_1m=0.25,
                output_price_per_1m=1.25,
                tier=PricingTier.FAST,
                provider="anthropic",
                model_name="Claude 3 Haiku",
            ),
            # AWS Bedrock - Claude models (same pricing via Bedrock)
            "anthropic.claude-sonnet-3-5-v2-20241022": ModelPricing(
                input_price_per_1m=3.00,
                output_price_per_1m=15.00,
                tier=PricingTier.STANDARD,
                provider="bedrock",
                model_name="Claude 3.5 Sonnet (Bedrock)",
            ),
            "anthropic.claude-3-5-sonnet-20240620-v1:0": ModelPricing(
                input_price_per_1m=3.00,
                output_price_per_1m=15.00,
                tier=PricingTier.STANDARD,
                provider="bedrock",
                model_name="Claude 3.5 Sonnet (Bedrock)",
            ),
            "anthropic.claude-3-opus-20240229-v1:0": ModelPricing(
                input_price_per_1m=15.00,
                output_price_per_1m=75.00,
                tier=PricingTier.FLAGSHIP,
                provider="bedrock",
                model_name="Claude 3 Opus (Bedrock)",
            ),
            "anthropic.claude-3-sonnet-20240229-v1:0": ModelPricing(
                input_price_per_1m=3.00,
                output_price_per_1m=15.00,
                tier=PricingTier.STANDARD,
                provider="bedrock",
                model_name="Claude 3 Sonnet (Bedrock)",
            ),
            "anthropic.claude-3-haiku-20240307-v1:0": ModelPricing(
                input_price_per_1m=0.25,
                output_price_per_1m=1.25,
                tier=PricingTier.FAST,
                provider="bedrock",
                model_name="Claude 3 Haiku (Bedrock)",
            ),
        }

        # Default pricing for unknown models
        self.default_pricing = {
            PricingTier.FLAGSHIP: ModelPricing(
                input_price_per_1m=15.00,
                output_price_per_1m=75.00,
                tier=PricingTier.FLAGSHIP,
                provider="unknown",
                model_name="Unknown Flagship Model",
            ),
            PricingTier.STANDARD: ModelPricing(
                input_price_per_1m=3.00,
                output_price_per_1m=15.00,
                tier=PricingTier.STANDARD,
                provider="unknown",
                model_name="Unknown Standard Model",
            ),
            PricingTier.FAST: ModelPricing(
                input_price_per_1m=0.25,
                output_price_per_1m=1.25,
                tier=PricingTier.FAST,
                provider="unknown",
                model_name="Unknown Fast Model",
            ),
        }

        # Cost tracking accumulators
        self.total_cost_usd = 0.0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.requests_tracked = 0
        self.cost_by_model: Dict[str, float] = {}
        self.cost_by_provider: Dict[str, float] = {}

    def calculate_cost(
        self, model: str, input_tokens: int, output_tokens: int, provider: Optional[str] = None
    ) -> Tuple[float, ModelPricing]:
        """
        Calculate cost for a request.

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

    def track_request_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        provider: Optional[str] = None,
    ) -> Dict[str, any]:
        """
        Calculate and track cost for a request.

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
        self.requests_tracked += 1

        # Track by model
        if model not in self.cost_by_model:
            self.cost_by_model[model] = 0.0
        self.cost_by_model[model] += cost_usd

        # Track by provider
        provider_name = provider or pricing.provider
        if provider_name not in self.cost_by_provider:
            self.cost_by_provider[provider_name] = 0.0
        self.cost_by_provider[provider_name] += cost_usd

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
            "tier": pricing.tier.value,
            "input_price_per_1m": pricing.input_price_per_1m,
            "output_price_per_1m": pricing.output_price_per_1m,
        }

    def get_pricing(self, model: str, provider: Optional[str] = None) -> ModelPricing:
        """
        Get pricing information for a model.

        Args:
            model: Model identifier
            provider: Optional provider name

        Returns:
            ModelPricing object
        """
        # Try exact match
        if model in self.pricing_data:
            return self.pricing_data[model]

        # Try to infer from model name
        model_lower = model.lower()

        # Infer tier from model name
        if "opus" in model_lower or "gpt-4" in model_lower:
            tier = PricingTier.FLAGSHIP
        elif "haiku" in model_lower or "instant" in model_lower:
            tier = PricingTier.FAST
        else:
            tier = PricingTier.STANDARD

        # Use default pricing for tier
        default = self.default_pricing[tier]

        # Update provider if provided
        if provider:
            return ModelPricing(
                input_price_per_1m=default.input_price_per_1m,
                output_price_per_1m=default.output_price_per_1m,
                tier=tier,
                provider=provider,
                model_name=model,
            )

        return default

    def add_model_pricing(
        self,
        model_id: str,
        input_price_per_1m: float,
        output_price_per_1m: float,
        provider: str,
        tier: PricingTier = PricingTier.STANDARD,
    ):
        """
        Add custom pricing for a model.

        Args:
            model_id: Model identifier
            input_price_per_1m: Input token price per 1M tokens
            output_price_per_1m: Output token price per 1M tokens
            provider: Provider name
            tier: Pricing tier
        """
        self.pricing_data[model_id] = ModelPricing(
            input_price_per_1m=input_price_per_1m,
            output_price_per_1m=output_price_per_1m,
            tier=tier,
            provider=provider,
            model_name=model_id,
        )

    def get_total_cost(self) -> float:
        """Get total accumulated cost in USD."""
        return round(self.total_cost_usd, 2)

    def get_cost_by_model(self) -> Dict[str, float]:
        """Get cost breakdown by model."""
        return {model: round(cost, 2) for model, cost in self.cost_by_model.items()}

    def get_cost_by_provider(self) -> Dict[str, float]:
        """Get cost breakdown by provider."""
        return {
            provider: round(cost, 2) for provider, cost in self.cost_by_provider.items()
        }

    def get_statistics(self) -> Dict[str, any]:
        """
        Get cost tracking statistics.

        Returns:
            Dictionary with statistics
        """
        avg_cost = (
            self.total_cost_usd / self.requests_tracked if self.requests_tracked > 0 else 0
        )

        return {
            "total_cost_usd": round(self.total_cost_usd, 2),
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "requests_tracked": self.requests_tracked,
            "average_cost_per_request": round(avg_cost, 6),
            "cost_by_model": self.get_cost_by_model(),
            "cost_by_provider": self.get_cost_by_provider(),
        }

    def reset_statistics(self):
        """Reset cost tracking statistics."""
        self.total_cost_usd = 0.0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.requests_tracked = 0
        self.cost_by_model = {}
        self.cost_by_provider = {}

    def estimate_cost(
        self, model: str, input_tokens: int, output_tokens: int
    ) -> Dict[str, any]:
        """
        Estimate cost without tracking (for planning).

        Args:
            model: Model identifier
            input_tokens: Estimated input tokens
            output_tokens: Estimated output tokens

        Returns:
            Cost estimate dictionary
        """
        cost_usd, pricing = self.calculate_cost(model, input_tokens, output_tokens)

        return {
            "estimated_cost_usd": round(cost_usd, 6),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "model": pricing.model_name,
            "tier": pricing.tier.value,
            "note": "Estimate only - not tracked in statistics",
        }


# Global cost tracker instance
cost_tracker = CostTracker()
