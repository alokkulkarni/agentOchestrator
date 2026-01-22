"""
Tech Insights Agent - AI-powered software engineering trends analysis.

Uses AI models through the model gateway to generate and validate insights about:
- Programming languages
- Tools and frameworks
- AI (Generative AI and RAG)
- Machine Learning
- Products and platforms

Features:
- AI-powered insight generation
- Output validation and quality checks
- Guardrails for content quality
- Fallback to curated insights
"""

import os
import json
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime
import aiohttp


class TechInsightsAgent:
    """AI-powered tech insights agent with validation and guardrails."""

    def __init__(self, gateway_url: str = "http://localhost:8585"):
        """
        Initialize tech insights agent.

        Args:
            gateway_url: Model gateway URL for AI generation
        """
        self.gateway_url = gateway_url
        self.use_ai = os.getenv("TECH_INSIGHTS_USE_AI", "true").lower() == "true"

        # Guardrails
        self.max_insights = 20
        self.min_insights = 10
        self.required_categories = ["ai", "languages", "tools", "ml"]
        self.required_fields = ["rank", "title", "category", "technical", "non_technical", "impact", "adoption", "source"]

    async def get_insights_async(
        self,
        category: Optional[str] = None,
        audience: Optional[str] = None,
        refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Get tech insights with AI generation and validation.

        Args:
            category: Filter by category (ai, languages, tools, ml)
            audience: Target audience (technical, non-technical, both)
            refresh: Force AI to regenerate insights

        Returns:
            Dict containing validated insights with metadata
        """
        # Step 1: Generate or retrieve insights
        if self.use_ai and refresh:
            insights = await self._generate_insights_with_ai()
        else:
            insights = self._get_curated_insights()

        # Step 2: Validate insights
        validation = self._validate_insights(insights)

        if not validation["valid"]:
            # Fallback to curated insights if validation fails
            insights = self._get_curated_insights()
            validation = self._validate_insights(insights)

        # Step 3: Filter by category if specified
        if category:
            insights = [i for i in insights if i.get("category") == category.lower()]

        # Step 4: Format based on audience
        formatted_insights = self._format_for_audience(insights, audience or "both")

        return {
            "total_insights": len(formatted_insights),
            "insights": formatted_insights,
            "categories": list(set(i["category"] for i in formatted_insights)),
            "timestamp": datetime.utcnow().isoformat(),
            "filters": {
                "category": category,
                "audience": audience or "both"
            },
            "validation": {
                "status": validation["valid"],
                "quality_score": validation.get("quality_score", 1.0),
                "issues": validation.get("issues", [])
            },
            "metadata": {
                "source": "Tech Insights Agent (AI-powered)" if self.use_ai else "Tech Insights Agent (Curated)",
                "version": "2026.1",
                "update_frequency": "on-demand" if self.use_ai else "monthly",
                "ai_generated": self.use_ai and refresh
            }
        }

    async def _generate_insights_with_ai(self) -> List[Dict[str, Any]]:
        """
        Generate insights using AI through model gateway.

        Returns:
            List of AI-generated insights
        """
        prompt = f"""You are a technology trends analyst. Generate the top 20 software engineering trends for 2026.

For EACH of the 20 trends, provide:
1. Title (clear, specific trend name)
2. Category (one of: ai, languages, tools, ml)
3. Technical perspective (150-200 words for engineers)
4. Non-technical perspective (100-150 words for business stakeholders)
5. Impact level (low, medium, high, very high)
6. Adoption stage (early, growing, steady, widespread)
7. Source (specific industry reports, research papers, documentation, or surveys that support this trend)

IMPORTANT:
- Cover ALL these categories: AI, Programming Languages, Tools/Frameworks, Machine Learning
- At least 5 trends in "ai" category
- At least 3 trends in "languages" category
- At least 8 trends in "tools" category
- At least 2 trends in "ml" category
- Focus on 2026 trends (current, not future speculation)
- Technical perspective: Include specific tools, frameworks, metrics, challenges
- Non-technical perspective: Use analogies, business value, real-world examples
- Source: Provide actual clickable URLs to industry reports, surveys, or official documentation (e.g., "https://survey.stackoverflow.co/2024, https://github.blog/octoverse"). Use real, valid URLs that users can visit.
- Be factual and specific, not vague or generic

Return ONLY valid JSON in this exact format:
{{
  "insights": [
    {{
      "rank": 1,
      "title": "Specific Trend Name",
      "category": "ai",
      "technical": "Detailed technical explanation...",
      "non_technical": "Business-friendly explanation...",
      "impact": "high",
      "adoption": "widespread",
      "source": "https://survey.stackoverflow.co/2024, https://www.gartner.com/en/newsroom/press-releases/gartner-ai-hype-cycle"
    }}
  ]
}}
"""

        try:
            response_text = await self._call_gateway(prompt, temperature=0.7, max_tokens=4000)

            # Parse JSON response
            insights_data = self._parse_json_response(response_text)

            if "insights" not in insights_data:
                raise ValueError("AI response missing 'insights' field")

            insights = insights_data["insights"]

            # Ensure we have exactly 20 insights
            if len(insights) < self.min_insights:
                raise ValueError(f"AI generated only {len(insights)} insights, need at least {self.min_insights}")

            # Limit to max insights
            insights = insights[:self.max_insights]

            return insights

        except Exception as e:
            # Fallback to curated insights on error
            return self._get_curated_insights()

    async def _call_gateway(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4000
    ) -> str:
        """
        Call model gateway for AI generation.

        Args:
            prompt: The prompt to send
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text response
        """
        async with aiohttp.ClientSession() as session:
            payload = {
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens
            }

            async with session.post(
                f"{self.gateway_url}/v1/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                response.raise_for_status()
                data = await response.json()

                return data["content"]

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Parse JSON from AI response, handling markdown code blocks.

        Args:
            response: Raw response text

        Returns:
            Parsed JSON dict
        """
        # Remove markdown code blocks if present
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        elif response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]

        response = response.strip()

        return json.loads(response)

    def _validate_insights(self, insights: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate insights against guardrails and quality standards.

        Args:
            insights: List of insights to validate

        Returns:
            Validation result with status and issues
        """
        issues = []
        quality_scores = []

        # Check count
        if len(insights) < self.min_insights:
            issues.append(f"Too few insights: {len(insights)} (minimum: {self.min_insights})")

        if len(insights) > self.max_insights:
            issues.append(f"Too many insights: {len(insights)} (maximum: {self.max_insights})")

        # Check category coverage
        categories = set(i.get("category") for i in insights if "category" in i)
        missing_categories = set(self.required_categories) - categories
        if missing_categories:
            issues.append(f"Missing required categories: {missing_categories}")

        # Validate each insight
        for idx, insight in enumerate(insights, 1):
            insight_issues = []

            # Check required fields
            for field in self.required_fields:
                if field not in insight:
                    insight_issues.append(f"Missing field: {field}")
                elif not insight[field]:
                    insight_issues.append(f"Empty field: {field}")

            # Validate field values
            if "category" in insight and insight["category"] not in ["ai", "languages", "tools", "ml"]:
                insight_issues.append(f"Invalid category: {insight['category']}")

            if "impact" in insight and insight["impact"] not in ["low", "medium", "high", "very high"]:
                insight_issues.append(f"Invalid impact: {insight['impact']}")

            if "adoption" in insight and insight["adoption"] not in ["early", "growing", "steady", "widespread"]:
                insight_issues.append(f"Invalid adoption: {insight['adoption']}")

            # Check text length (quality check)
            technical_len = len(insight.get("technical", ""))
            non_technical_len = len(insight.get("non_technical", ""))

            if technical_len < 100:
                insight_issues.append("Technical perspective too short")
            elif technical_len > 800:
                insight_issues.append("Technical perspective too long")

            if non_technical_len < 50:
                insight_issues.append("Non-technical perspective too short")
            elif non_technical_len > 600:
                insight_issues.append("Non-technical perspective too long")

            # Calculate quality score for this insight
            if insight_issues:
                issues.append(f"Insight #{idx} ({insight.get('title', 'Unknown')}): {', '.join(insight_issues)}")
                quality_scores.append(0.5)
            else:
                quality_scores.append(1.0)

        # Overall quality score
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

        return {
            "valid": len(issues) == 0,
            "quality_score": avg_quality,
            "issues": issues,
            "insights_count": len(insights),
            "categories_covered": list(categories)
        }

    def _format_for_audience(
        self,
        insights: List[Dict[str, Any]],
        audience: str
    ) -> List[Dict[str, Any]]:
        """
        Format insights based on target audience.

        Args:
            insights: List of insights
            audience: Target audience (technical, non-technical, both)

        Returns:
            Formatted insights
        """
        if audience == "technical":
            return [
                {
                    "rank": i["rank"],
                    "title": i["title"],
                    "category": i["category"],
                    "insight": i["technical"],
                    "impact": i["impact"],
                    "adoption": i["adoption"],
                    "source": i.get("source", "N/A")
                }
                for i in insights
            ]
        elif audience == "non-technical":
            return [
                {
                    "rank": i["rank"],
                    "title": i["title"],
                    "category": i["category"],
                    "insight": i["non_technical"],
                    "impact": i["impact"],
                    "adoption": i["adoption"],
                    "source": i.get("source", "N/A")
                }
                for i in insights
            ]
        else:  # both
            return insights

    def _get_curated_insights(self) -> List[Dict[str, Any]]:
        """
        Get curated (static) insights as fallback.

        Returns:
            List of curated insights
        """
        return [
            {
                "rank": 1,
                "title": "Large Language Models (LLMs) in Production",
                "category": "ai",
                "technical": "Organizations are deploying LLMs with custom fine-tuning, RAG architectures, and prompt engineering frameworks. Key considerations: token costs, latency optimization (via caching and streaming), model selection (GPT-4, Claude, Llama), and safety guardrails. Focus on evaluation metrics like RAGAS for RAG systems.",
                "non_technical": "Companies are using AI assistants that can understand and generate human-like text. These tools help automate customer service, content creation, and data analysis. The challenge is making them reliable, cost-effective, and safe for business use.",
                "impact": "high",
                "adoption": "widespread",
                "source": "https://www.gartner.com/en/newsroom/press-releases/gartner-ai-hype-cycle, https://www.mckinsey.com/capabilities/quantumblack/our-insights/the-state-of-ai"
            },
            {
                "rank": 2,
                "title": "Retrieval-Augmented Generation (RAG) Architecture",
                "category": "ai",
                "technical": "RAG systems combine vector databases (Pinecone, Weaviate, Chroma) with LLMs to provide context-aware responses. Key components: embedding models (OpenAI, Cohere), semantic search, reranking, and hybrid retrieval. Challenges include chunk size optimization, retrieval accuracy, and maintaining context windows.",
                "non_technical": "Imagine giving an AI access to your company's knowledge base so it can answer questions accurately using your specific data. RAG makes AI assistants smarter by letting them look up relevant information before responding, like having an expert with instant access to all your documents.",
                "impact": "high",
                "adoption": "growing",
                "source": "https://python.langchain.com/docs/tutorials/rag, https://www.databricks.com/blog/category/research"
            },
            {
                "rank": 3,
                "title": "Rust for Systems Programming",
                "category": "languages",
                "technical": "Rust adoption accelerating for systems programming, replacing C/C++ in performance-critical applications. Memory safety without garbage collection, async runtime (Tokio), and zero-cost abstractions. Used in CLI tools (ripgrep), web frameworks (Axum, Actix), and cloud infrastructure (AWS Lambda, Cloudflare Workers).",
                "non_technical": "A new programming language that's extremely fast and prevents common bugs that crash software. Major tech companies are switching to Rust because it makes their systems more reliable while maintaining high performance. Think of it as a safer, modern alternative to older low-level languages.",
                "impact": "high",
                "adoption": "growing",
                "source": "https://survey.stackoverflow.co/2024, https://foundation.rust-lang.org/news/rust-foundation-annual-report"
            },
            {
                "rank": 4,
                "title": "Platform Engineering & Internal Developer Platforms (IDPs)",
                "category": "tools",
                "technical": "Platform teams building golden paths: standardized deployment pipelines, service templates, and self-service infrastructure. Tools: Backstage, Port, Humanitec. Focus on developer experience metrics (DORA), reducing cognitive load, and abstracting complexity while maintaining flexibility.",
                "non_technical": "Companies are creating internal 'app stores' for developers - standardized ways to quickly launch new projects, deploy code, and manage infrastructure. This lets developers focus on building features instead of configuring servers, much like how an iPhone user doesn't worry about the underlying hardware.",
                "impact": "high",
                "adoption": "growing",
                "source": "https://www.puppet.com/resources/state-of-platform-engineering, https://dora.dev"
            },
            {
                "rank": 5,
                "title": "AI Code Assistants (GitHub Copilot, Claude Code, Cursor)",
                "category": "ai",
                "technical": "AI-powered IDEs and code completion reaching 40-60% code acceptance rates. Context-aware suggestions using codebase embeddings, multi-file editing, and natural language to code. Integration with development workflows via CLI tools, IDE extensions, and terminal interfaces. Key consideration: code quality vs velocity trade-offs.",
                "non_technical": "Programmers now have AI assistants that write code alongside them, like having an expert pair programmer available 24/7. These tools understand the project context and can generate entire functions, fix bugs, and even explain complex code in plain English, dramatically speeding up development.",
                "impact": "very high",
                "adoption": "widespread",
                "source": "https://github.blog/news-insights/octoverse, https://www.jetbrains.com/lp/devecosystem-2024"
            },
            {
                "rank": 6,
                "title": "Edge Computing & Cloudflare Workers",
                "category": "tools",
                "technical": "Serverless functions running at edge locations (300+ cities worldwide) with sub-10ms cold starts. V8 isolates providing better performance than containers. Use cases: API gateways, A/B testing, authentication, and full-stack apps using Durable Objects for stateful edge computing.",
                "non_technical": "Instead of running applications in a few large data centers, software now runs in hundreds of locations worldwide, closer to users. This means faster load times (like having a coffee shop on every corner instead of just downtown), especially for global applications.",
                "impact": "medium",
                "adoption": "growing",
                "source": "https://developers.cloudflare.com/workers, https://www.gartner.com/en/information-technology/insights/edge-computing"
            },
            {
                "rank": 7,
                "title": "TypeScript Dominance in Frontend Development",
                "category": "languages",
                "technical": "TypeScript usage exceeding 80% in new frontend projects. Strong typing catching bugs at compile time, excellent IDE support, and ecosystem maturity. Recent improvements: satisfies operator, const type parameters, and decorators. Integration with modern frameworks (Next.js, Remix, Astro) is seamless.",
                "non_technical": "JavaScript (the language of web browsers) now has a popular variant that catches errors before code runs, like spell-check for programming. This prevents bugs from reaching users and makes large web applications more maintainable, which is why nearly all new web projects use it.",
                "impact": "high",
                "adoption": "widespread",
                "source": "https://stateofjs.com, https://www.typescriptlang.org/docs/handbook/release-notes/overview.html"
            },
            {
                "rank": 8,
                "title": "Vector Databases for AI Applications",
                "category": "ai",
                "technical": "Specialized databases for storing and querying embeddings: Pinecone (managed), Weaviate (open-source), Qdrant (Rust-based), and pgvector (Postgres extension). Key features: similarity search, filtering, hybrid search, and horizontal scaling. Critical for RAG, semantic search, and recommendation systems.",
                "non_technical": "New types of databases designed specifically for AI to find similar items (like 'find products similar to this one' or 'what documents are related to this question'). They power features like smart search, personalized recommendations, and chatbots that understand context.",
                "impact": "high",
                "adoption": "growing",
                "source": "https://www.pinecone.io/learn/vector-database, https://weaviate.io/blog"
            },
            {
                "rank": 9,
                "title": "WebAssembly (WASM) Beyond the Browser",
                "category": "tools",
                "technical": "WASM runtimes (Wasmtime, WasmEdge) enabling portable, sandboxed execution. Use cases: edge computing, plugin systems, and polyglot applications. WASI providing system interface standardization. Languages compiling to WASM: Rust, Go, C/C++, AssemblyScript. Performance near-native with security isolation.",
                "non_technical": "A technology that lets any programming language run anywhere - in browsers, on servers, or on edge devices - with near-native speed and built-in security. It's like having a universal translator that makes different programming languages work together efficiently and safely.",
                "impact": "medium",
                "adoption": "early",
                "source": "https://www.w3.org/wasm, https://bytecodealliance.org"
            },
            {
                "rank": 10,
                "title": "Observable & Testable AI Systems",
                "category": "ai",
                "technical": "LLM observability platforms (Langsmith, Weights & Biases, Helicone) tracking prompts, responses, costs, and latency. Evaluation frameworks using datasets, assertions, and LLM-as-judge patterns. Key metrics: hallucination rate, context relevance, answer faithfulness. Integration with CI/CD for regression testing.",
                "non_technical": "As companies deploy AI systems, they need ways to monitor if the AI is working correctly, costing too much, or giving wrong answers. New tools track every AI interaction, measure quality, and alert teams to problems - like having a dashboard for your AI systems' health.",
                "impact": "high",
                "adoption": "growing",
                "source": "https://docs.smith.langchain.com, https://wandb.ai/site/solutions/llmops"
            },
            {
                "rank": 11,
                "title": "Multi-Modal AI (Vision, Audio, Text)",
                "category": "ai",
                "technical": "Models processing multiple input types: GPT-4V (vision), Whisper (speech-to-text), DALL-E 3 (text-to-image). Applications: document understanding, video analysis, accessibility features. Technical challenges: context window management across modalities, latency optimization, and cost management for image tokens.",
                "non_technical": "AI systems that can now see images, hear audio, read text, and even generate images - all working together. This enables applications like AI that can analyze medical scans, transcribe meetings while understanding visual presentations, or create illustrations from descriptions.",
                "impact": "high",
                "adoption": "growing",
                "source": "https://openai.com/research, https://www.anthropic.com/news/claude-3-5-sonnet"
            },
            {
                "rank": 12,
                "title": "Python 3.12+ Performance Improvements",
                "category": "languages",
                "technical": "Python 3.12 delivers 5-10% speedup via adaptive interpreter. PEP 695 type parameter syntax improving generics. Upcoming: 3.13 removes GIL for true parallelism, 3.14 targets JIT compilation. Performance-critical code using PyPy or Cython. Type hints adoption improving static analysis and IDE support.",
                "non_technical": "Python, the most popular programming language for AI and data science, is getting significantly faster. New versions remove old limitations that prevented it from using multiple CPU cores effectively, making data processing and AI applications run much quicker.",
                "impact": "medium",
                "adoption": "widespread",
                "source": "https://docs.python.org/3/whatsnew/3.12.html, https://peps.python.org/pep-0703"
            },
            {
                "rank": 13,
                "title": "Infrastructure as Code (IaC) with Terraform/Pulumi",
                "category": "tools",
                "technical": "Cloud infrastructure managed as code: Terraform (HCL), Pulumi (real languages: Python, TypeScript, Go), and CDK. Benefits: version control, repeatability, and drift detection. Challenges: state management, testing strategies, and team collaboration. GitOps workflows with automated deployments via CI/CD.",
                "non_technical": "Instead of manually clicking through cloud provider interfaces to set up servers, teams write code that automatically creates and manages infrastructure. This makes it easy to replicate environments, track changes, and recover from disasters - like having blueprints for your entire tech infrastructure.",
                "impact": "high",
                "adoption": "widespread",
                "source": "https://www.hashicorp.com/state-of-the-cloud, https://www.cncf.io/reports/cncf-annual-report-2023"
            },
            {
                "rank": 14,
                "title": "AI Agents & Autonomous Systems",
                "category": "ai",
                "technical": "LLM-powered agents using ReAct pattern (reasoning + acting), function calling, and tool use. Frameworks: LangChain, AutoGPT, AgentGPT. Architectures: single-agent (task-specific) vs multi-agent (orchestration). Challenges: reliability, determinism, cost management, and preventing infinite loops.",
                "non_technical": "AI systems that can break down complex tasks, use multiple tools, and work autonomously to achieve goals. Instead of just answering questions, these agents can plan, execute tasks, and adapt - like having an AI assistant that can actually do work, not just provide advice.",
                "impact": "high",
                "adoption": "early",
                "source": "https://hai.stanford.edu/research, https://github.com/Significant-Gravitas/AutoGPT"
            },
            {
                "rank": 15,
                "title": "Container Orchestration Evolution (Kubernetes Alternatives)",
                "category": "tools",
                "technical": "Simpler alternatives emerging: Nomad (HashiCorp), Docker Swarm, and serverless containers (AWS Fargate, Cloud Run). K8s remaining dominant for complex workloads but overkill for many use cases. Focus shifting to developer experience, cost optimization, and operational simplicity.",
                "non_technical": "While Kubernetes remains the standard for managing containers (like shipping containers for software), lighter alternatives are gaining traction. Companies are realizing they don't always need industrial-scale solutions - sometimes a pickup truck works better than a cargo ship.",
                "impact": "medium",
                "adoption": "steady",
                "source": "https://www.cncf.io/reports/cncf-annual-survey-2023, https://www.docker.com/blog"
            },
            {
                "rank": 16,
                "title": "GraphQL Maturity & Federation",
                "category": "tools",
                "technical": "GraphQL adoption stabilizing with Apollo Federation enabling microservices integration. Key patterns: schema stitching, dataloaders for N+1 prevention, and persisted queries. Challenges: caching complexity, query cost analysis, and monitoring. Alternative: tRPC for TypeScript end-to-end type safety without code generation.",
                "non_technical": "A modern way for applications to request data from servers, letting clients ask for exactly what they need in one request. It's like ordering a custom meal instead of getting a fixed combo - more efficient and flexible, especially for mobile apps where bandwidth matters.",
                "impact": "medium",
                "adoption": "steady",
                "source": "https://graphql.org/foundation, https://www.apollographql.com/blog/announcement/backend/2023-graphql-survey-results"
            },
            {
                "rank": 17,
                "title": "ML Ops & Model Deployment Platforms",
                "category": "ml",
                "technical": "End-to-end ML platforms: Databricks, Weights & Biases, MLflow. Key features: experiment tracking, model registry, automated retraining, and A/B testing. Deployment patterns: batch inference, real-time endpoints, and edge deployment. Focus on reproducibility, monitoring (data drift, model decay), and CI/CD for ML.",
                "non_technical": "Just as DevOps helped software teams deploy apps faster, MLOps helps data science teams deploy AI models to production reliably. These platforms automate the journey from experiment to production, making AI projects more successful and maintainable.",
                "impact": "high",
                "adoption": "growing",
                "source": "https://www.databricks.com/resources/ebook/state-of-data-ai-2023, https://mlflow.org"
            },
            {
                "rank": 18,
                "title": "Zero Trust Security Architecture",
                "category": "tools",
                "technical": "Never trust, always verify: identity-based access (OAuth2, OIDC), service mesh (Istio, Linkerd), mutual TLS, and continuous authentication. Tools: HashiCorp Vault for secrets, OPA for policy enforcement, and SPIFFE/SPIRE for workload identity. Moving beyond perimeter security to identity-centric model.",
                "non_technical": "Traditional security was like a castle with walls - once inside, you're trusted. Zero Trust assumes no one is trusted by default. Every request is verified, every connection is encrypted, and access is granted based on identity, not location. It's security fit for cloud computing and remote work.",
                "impact": "high",
                "adoption": "growing",
                "source": "https://csrc.nist.gov/publications/detail/sp/800-207/final, https://www.forrester.com/research"
            },
            {
                "rank": 19,
                "title": "Real-time Collaboration Tools & CRDTs",
                "category": "tools",
                "technical": "Conflict-free Replicated Data Types (CRDTs) enabling real-time collaboration like Google Docs. Libraries: Yjs, Automerge, Diamond Types. Use cases: collaborative editing, multiplayer experiences, and offline-first apps. Challenges: merge complexity, bandwidth optimization, and persistence strategies.",
                "non_technical": "Technology that powers real-time collaboration in apps like Google Docs, Figma, and Notion. Multiple people can edit simultaneously without conflicts, changes sync instantly, and it works even offline. This is becoming standard for modern productivity tools.",
                "impact": "medium",
                "adoption": "growing",
                "source": "https://crdt.tech, https://www.figma.com/blog/how-figmas-multiplayer-technology-works"
            },
            {
                "rank": 20,
                "title": "Sustainable Computing & Green Software",
                "category": "tools",
                "technical": "Carbon-aware computing: scheduling workloads during low-carbon periods, efficient algorithms, and hardware utilization optimization. Tools: Green Software Foundation metrics, carbon intensity APIs, and energy-efficient languages (Rust, Go vs Python). Focus on measuring and reducing carbon footprint of software systems.",
                "non_technical": "The tech industry is focusing on reducing energy consumption and carbon emissions from software. This includes running applications when renewable energy is available, optimizing code to use less power, and choosing energy-efficient technologies. It's about making software environmentally responsible.",
                "impact": "medium",
                "adoption": "early",
                "source": "https://greensoftware.foundation, https://www.linuxfoundation.org/research/the-2023-state-of-energy-and-climate"
            }
        ]


# Synchronous wrapper for orchestrator
def get_tech_insights(**kwargs) -> Dict[str, Any]:
    """
    Synchronous wrapper for tech insights agent.

    Args:
        **kwargs: Optional parameters (category, audience, refresh, gateway_url)

    Returns:
        Tech insights result dict
    """
    # Get gateway URL from kwargs or environment
    gateway_url = kwargs.get("gateway_url", os.getenv("MODEL_GATEWAY_URL", "http://localhost:8585"))

    # Extract parameters
    category = kwargs.get("category")
    audience = kwargs.get("audience")
    refresh = kwargs.get("refresh", False)

    # Create agent and run
    agent = TechInsightsAgent(gateway_url=gateway_url)

    # Run async function in sync context
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            agent.get_insights_async(category=category, audience=audience, refresh=refresh)
        )
        return result
    finally:
        loop.close()


# Test the agent
if __name__ == "__main__":
    import sys

    print("Testing Tech Insights Agent (AI-Powered)\n")
    print("=" * 80)

    # Test 1: Get curated insights
    print("\n1. Getting curated insights (no AI):")
    print("-" * 80)

    result = get_tech_insights(category=None, audience="both")

    print(f"\n✅ Retrieved {result['total_insights']} insights")
    print(f"Categories: {', '.join(result['categories'])}")
    print(f"Source: {result['metadata']['source']}")
    print(f"Validation: {'✅ Valid' if result['validation']['status'] else '❌ Invalid'}")
    print(f"Quality Score: {result['validation']['quality_score']:.2%}")

    if result['validation']['issues']:
        print(f"\nIssues: {len(result['validation']['issues'])}")
        for issue in result['validation']['issues'][:3]:
            print(f"  - {issue}")

    # Show first insight
    if result['insights']:
        first = result['insights'][0]
        print(f"\nFirst Insight: {first['title']}")
        print(f"  Category: {first['category']}")
        print(f"  Impact: {first['impact']} | Adoption: {first['adoption']}")

    print("\n" + "=" * 80)
    print("\n💡 To test AI generation:")
    print("   1. Ensure model gateway is running on http://localhost:8585")
    print("   2. Set TECH_INSIGHTS_USE_AI=true")
    print("   3. Call get_tech_insights(refresh=True)")
    print("\n" + "=" * 80)
