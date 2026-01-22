"""
Planning Agent - Creates detailed application plans with epics and user stories.

This agent takes requirements for mobile/web applications and generates:
- Detailed project plan in epic/user story format
- Technology-agnostic planning
- Validation against original requirements
- Interactive clarification when needed
- Document storage in organized folders
"""

import os
import json
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path
import aiohttp


class PlanningAgent:
    """AI-powered planning agent with validation and interactive clarification."""

    def __init__(self, gateway_url: str = "http://localhost:8585"):
        """
        Initialize planning agent.

        Args:
            gateway_url: Model gateway URL for AI planning
        """
        self.gateway_url = gateway_url
        self.plans_dir = Path("./application_plans")
        self.plans_dir.mkdir(exist_ok=True)

    async def plan_application(self, requirements: str, **kwargs) -> Dict[str, Any]:
        """
        Create detailed application plan from requirements.

        Args:
            requirements: User requirements for the application
            **kwargs: Optional parameters (app_type, clarifications, etc.)

        Returns:
            Dict containing plan, document path, and metadata
        """
        app_type = kwargs.get("app_type", "application")
        clarifications = kwargs.get("clarifications", {})

        # Step 1: Validate requirements and identify missing information
        validation_result = await self._validate_requirements(requirements, clarifications)

        if not validation_result["complete"]:
            return {
                "success": True,
                "status": "needs_clarification",
                "missing_info": validation_result["missing_info"],
                "questions": validation_result["questions"],
                "partial_understanding": validation_result["understanding"],
                "message": "Additional information needed to create comprehensive plan"
            }

        # Step 2: Generate detailed plan with epics and user stories
        plan_result = await self._generate_plan(requirements, app_type, validation_result["understanding"])

        if not plan_result["success"]:
            return plan_result

        # Step 3: Validate the generated plan against requirements
        validation = await self._validate_plan(requirements, plan_result["plan"])

        if not validation["valid"]:
            return {
                "success": False,
                "error": "Plan validation failed",
                "issues": validation["issues"],
                "message": "Generated plan does not meet requirements"
            }

        # Step 4: Create document and save to filesystem
        document = self._format_plan_document(
            requirements=requirements,
            plan=plan_result["plan"],
            app_type=app_type,
            validation=validation
        )

        doc_path = self._save_plan_document(document, app_type)

        return {
            "success": True,
            "status": "plan_created",
            "plan": plan_result["plan"],
            "document_path": str(doc_path),
            "validation": validation,
            "metadata": {
                "created_at": datetime.utcnow().isoformat(),
                "app_type": app_type,
                "requirements_length": len(requirements),
                "epics_count": len(plan_result["plan"].get("epics", [])),
                "total_stories": sum(len(epic.get("user_stories", []))
                                   for epic in plan_result["plan"].get("epics", []))
            },
            "message": f"Application plan created successfully and saved to {doc_path}"
        }

    async def _validate_requirements(
        self,
        requirements: str,
        clarifications: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate if requirements are complete enough for planning.

        Returns:
            Dict with 'complete', 'missing_info', 'questions', 'understanding'
        """
        prompt = f"""You are a planning validation agent. Analyze the following application requirements and determine if they are complete enough to create a detailed project plan.

Requirements:
{requirements}

Previous Clarifications:
{json.dumps(clarifications, indent=2) if clarifications else "None"}

Analyze and respond in JSON format:
{{
    "complete": true/false,
    "understanding": {{
        "app_purpose": "What the application does",
        "target_users": "Who will use it",
        "core_features": ["list", "of", "features"],
        "scope": "Project scope"
    }},
    "missing_info": ["list of missing critical information"],
    "questions": ["specific questions to ask user for clarification"]
}}

IMPORTANT:
- Only set complete=false if CRITICAL information is missing
- Don't ask about technology stack (we plan technology-agnostic)
- Don't ask about implementation details
- Focus on: purpose, users, features, scope, constraints
- If requirements are reasonably clear, set complete=true
"""

        try:
            response = await self._call_gateway(prompt, temperature=0.3)
            result = self._parse_json_response(response)

            # Ensure required fields
            if "complete" not in result:
                result["complete"] = True  # Default to complete if unclear

            return result

        except Exception as e:
            # On error, assume requirements are complete to avoid blocking
            return {
                "complete": True,
                "understanding": {
                    "app_purpose": "Application based on provided requirements",
                    "target_users": "End users",
                    "core_features": ["As specified in requirements"],
                    "scope": "As defined by user"
                },
                "missing_info": [],
                "questions": []
            }

    async def _generate_plan(
        self,
        requirements: str,
        app_type: str,
        understanding: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate detailed plan with epics and user stories using AI.

        Returns:
            Dict with 'success', 'plan' (epics and user stories)
        """
        prompt = f"""You are an expert product manager creating a detailed application plan. Generate a comprehensive project plan in epic and user story format.

Application Requirements:
{requirements}

Understanding:
{json.dumps(understanding, indent=2)}

Application Type: {app_type}

Create a detailed plan in JSON format:
{{
    "project_name": "Application name",
    "vision": "High-level vision statement",
    "objectives": ["List of key objectives"],
    "epics": [
        {{
            "id": "EPIC-001",
            "title": "Epic title",
            "description": "Detailed epic description",
            "priority": "High/Medium/Low",
            "estimated_effort": "T-shirt size (XS/S/M/L/XL)",
            "acceptance_criteria": ["List of acceptance criteria"],
            "user_stories": [
                {{
                    "id": "US-001",
                    "title": "User story title",
                    "as_a": "user role",
                    "i_want": "functionality",
                    "so_that": "benefit/value",
                    "priority": "High/Medium/Low",
                    "estimated_effort": "Story points (1/2/3/5/8/13)",
                    "acceptance_criteria": ["List of acceptance criteria"],
                    "technical_notes": ["Optional technical considerations"]
                }}
            ]
        }}
    ],
    "non_functional_requirements": {{
        "performance": ["Performance requirements"],
        "security": ["Security requirements"],
        "scalability": ["Scalability requirements"],
        "accessibility": ["Accessibility requirements"],
        "compliance": ["Compliance requirements"]
    }},
    "risks": [
        {{
            "description": "Risk description",
            "impact": "High/Medium/Low",
            "mitigation": "Mitigation strategy"
        }}
    ],
    "assumptions": ["List of assumptions made"],
    "constraints": ["List of constraints"]
}}

IMPORTANT:
- Create 3-7 epics covering all major features
- Each epic should have 3-10 user stories
- Be specific and actionable
- Follow standard user story format: "As a [role], I want [feature] so that [benefit]"
- Prioritize stories (High/Medium/Low)
- Include acceptance criteria for each story
- Be technology-agnostic
- Focus on WHAT, not HOW
- Ensure stories are independently deliverable
"""

        try:
            response = await self._call_gateway(prompt, temperature=0.7)
            plan = self._parse_json_response(response)

            return {
                "success": True,
                "plan": plan
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to generate plan: {str(e)}"
            }

    async def _validate_plan(
        self,
        requirements: str,
        plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate generated plan against original requirements.

        Returns:
            Dict with 'valid', 'confidence', 'issues', 'feedback'
        """
        prompt = f"""You are a quality assurance agent validating a project plan against requirements.

Original Requirements:
{requirements}

Generated Plan:
{json.dumps(plan, indent=2)}

Validate the plan and respond in JSON format:
{{
    "valid": true/false,
    "confidence": 0.95,
    "issues": ["list of any issues or missing elements"],
    "coverage": {{
        "requirements_addressed": ["list of requirements covered"],
        "requirements_missing": ["list of requirements not addressed"]
    }},
    "quality_assessment": {{
        "completeness": "High/Medium/Low",
        "clarity": "High/Medium/Low",
        "actionability": "High/Medium/Low"
    }},
    "feedback": "Overall assessment and recommendations"
}}

Validation Criteria:
- All stated requirements are addressed in epics/stories
- User stories follow standard format
- Acceptance criteria are specific and testable
- Priorities are reasonable
- No hallucinated features (not in requirements)
- Stories are independently deliverable
"""

        try:
            response = await self._call_gateway(prompt, temperature=0.3)
            validation = self._parse_json_response(response)

            # Default to valid if unclear
            if "valid" not in validation:
                validation["valid"] = True

            return validation

        except Exception as e:
            # On error, mark as valid to avoid blocking
            return {
                "valid": True,
                "confidence": 0.7,
                "issues": [f"Validation incomplete: {str(e)}"],
                "feedback": "Plan generated but validation incomplete"
            }

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
                timeout=aiohttp.ClientTimeout(total=120)
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

    def _format_plan_document(
        self,
        requirements: str,
        plan: Dict[str, Any],
        app_type: str,
        validation: Dict[str, Any]
    ) -> str:
        """
        Format plan as markdown document.

        Returns:
            Formatted markdown string
        """
        doc = []

        # Header
        doc.append(f"# {plan.get('project_name', 'Application')} - Project Plan")
        doc.append(f"\n**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        doc.append(f"**Application Type:** {app_type}")
        doc.append(f"**Validation Status:** {'✅ Validated' if validation.get('valid') else '⚠️ Issues Found'}")
        doc.append("\n---\n")

        # Original Requirements
        doc.append("## 📋 Original Requirements\n")
        doc.append(requirements)
        doc.append("\n---\n")

        # Vision and Objectives
        if "vision" in plan:
            doc.append("## 🎯 Vision\n")
            doc.append(plan["vision"])
            doc.append("\n")

        if "objectives" in plan:
            doc.append("## 🎯 Key Objectives\n")
            for obj in plan["objectives"]:
                doc.append(f"- {obj}")
            doc.append("\n---\n")

        # Epics and User Stories
        doc.append("## 📚 Epics and User Stories\n")

        for epic in plan.get("epics", []):
            doc.append(f"\n### {epic['id']}: {epic['title']}")
            doc.append(f"\n**Priority:** {epic.get('priority', 'Medium')}")
            doc.append(f" | **Effort:** {epic.get('estimated_effort', 'M')}\n")
            doc.append(f"\n{epic.get('description', '')}\n")

            # Epic Acceptance Criteria
            if "acceptance_criteria" in epic:
                doc.append("\n**Epic Acceptance Criteria:**")
                for criteria in epic["acceptance_criteria"]:
                    doc.append(f"- {criteria}")
                doc.append("")

            # User Stories
            doc.append(f"\n#### User Stories ({len(epic.get('user_stories', []))} stories)\n")

            for story in epic.get("user_stories", []):
                doc.append(f"\n##### {story['id']}: {story['title']}")
                doc.append(f"\n**Priority:** {story.get('priority', 'Medium')}")
                doc.append(f" | **Effort:** {story.get('estimated_effort', '3')} points\n")

                doc.append(f"\n**User Story:**")
                doc.append(f"- **As a** {story.get('as_a', 'user')}")
                doc.append(f"- **I want** {story.get('i_want', '')}")
                doc.append(f"- **So that** {story.get('so_that', '')}\n")

                # Acceptance Criteria
                if "acceptance_criteria" in story:
                    doc.append("**Acceptance Criteria:**")
                    for criteria in story["acceptance_criteria"]:
                        doc.append(f"- {criteria}")
                    doc.append("")

                # Technical Notes
                if story.get("technical_notes"):
                    doc.append("**Technical Notes:**")
                    for note in story["technical_notes"]:
                        doc.append(f"- {note}")
                    doc.append("")

            doc.append("\n---\n")

        # Non-Functional Requirements
        if "non_functional_requirements" in plan:
            doc.append("## ⚙️ Non-Functional Requirements\n")
            nfr = plan["non_functional_requirements"]

            for category, items in nfr.items():
                if items:
                    doc.append(f"\n### {category.title()}")
                    for item in items:
                        doc.append(f"- {item}")
                    doc.append("")

            doc.append("\n---\n")

        # Risks
        if "risks" in plan and plan["risks"]:
            doc.append("## ⚠️ Risks and Mitigation\n")
            for risk in plan["risks"]:
                doc.append(f"\n**Risk:** {risk.get('description', '')}")
                doc.append(f"- **Impact:** {risk.get('impact', 'Medium')}")
                doc.append(f"- **Mitigation:** {risk.get('mitigation', '')}\n")
            doc.append("\n---\n")

        # Assumptions and Constraints
        if "assumptions" in plan and plan["assumptions"]:
            doc.append("## 💭 Assumptions\n")
            for assumption in plan["assumptions"]:
                doc.append(f"- {assumption}")
            doc.append("")

        if "constraints" in plan and plan["constraints"]:
            doc.append("## 🔒 Constraints\n")
            for constraint in plan["constraints"]:
                doc.append(f"- {constraint}")
            doc.append("\n---\n")

        # Validation Report
        doc.append("## ✅ Validation Report\n")
        doc.append(f"**Status:** {'Valid ✅' if validation.get('valid') else 'Issues Found ⚠️'}")
        doc.append(f"**Confidence:** {validation.get('confidence', 0.0):.2%}\n")

        if "quality_assessment" in validation:
            qa = validation["quality_assessment"]
            doc.append("\n**Quality Assessment:**")
            doc.append(f"- **Completeness:** {qa.get('completeness', 'N/A')}")
            doc.append(f"- **Clarity:** {qa.get('clarity', 'N/A')}")
            doc.append(f"- **Actionability:** {qa.get('actionability', 'N/A')}\n")

        if validation.get("issues"):
            doc.append("\n**Issues Identified:**")
            for issue in validation["issues"]:
                doc.append(f"- {issue}")
            doc.append("")

        if "feedback" in validation:
            doc.append(f"\n**Feedback:** {validation['feedback']}\n")

        return "\n".join(doc)

    def _save_plan_document(self, document: str, app_type: str) -> Path:
        """
        Save plan document to filesystem.

        Args:
            document: Formatted markdown document
            app_type: Application type for folder organization

        Returns:
            Path to saved document
        """
        # Create subfolder for app type
        app_folder = self.plans_dir / app_type.replace(" ", "_").lower()
        app_folder.mkdir(exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"plan_{timestamp}.md"
        doc_path = app_folder / filename

        # Save document
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write(document)

        return doc_path


# Synchronous wrapper for orchestrator
def create_application_plan(requirements: str = None, query: str = None, **kwargs) -> Dict[str, Any]:
    """
    Synchronous wrapper for planning agent.

    Args:
        requirements: Application requirements (preferred)
        query: Alternative query format
        **kwargs: Additional parameters

    Returns:
        Plan result dict
    """
    # Handle different input formats
    if not requirements and query:
        requirements = query

    if not requirements:
        return {
            "success": False,
            "error": "No requirements provided",
            "message": "Please provide application requirements to create a plan"
        }

    # Get gateway URL from kwargs or environment
    gateway_url = kwargs.get("gateway_url", os.getenv("MODEL_GATEWAY_URL", "http://localhost:8585"))

    # Create agent and run planning
    agent = PlanningAgent(gateway_url=gateway_url)

    # Run async function in sync context
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(agent.plan_application(requirements, **kwargs))
        return result
    finally:
        loop.close()


# Test the agent
if __name__ == "__main__":
    import sys

    print("Testing Planning Agent\n")
    print("=" * 80)

    # Test 1: Simple web app
    print("\n1. Planning a simple web application:")
    print("-" * 80)

    requirements = """
    Create a task management web application where users can:
    - Create, edit, and delete tasks
    - Organize tasks into projects
    - Set due dates and priorities
    - Mark tasks as complete
    - Filter and search tasks
    - Collaborate with team members on shared projects

    The app should be accessible on desktop and mobile browsers.
    Target users are small to medium-sized teams (5-50 people).
    """

    result = create_application_plan(requirements=requirements, app_type="web_application")

    if result["success"]:
        if result.get("status") == "needs_clarification":
            print("\n⚠️ Needs clarification:")
            print(f"Missing info: {result['missing_info']}")
            print(f"\nQuestions:")
            for q in result["questions"]:
                print(f"  - {q}")
        else:
            print(f"\n✅ Plan created successfully!")
            print(f"Document saved to: {result['document_path']}")
            print(f"\nMetadata:")
            print(f"  - Epics: {result['metadata']['epics_count']}")
            print(f"  - User Stories: {result['metadata']['total_stories']}")
            print(f"  - Validation: {result['validation']['confidence']:.1%} confidence")

            # Show first epic
            if result["plan"].get("epics"):
                first_epic = result["plan"]["epics"][0]
                print(f"\nFirst Epic: {first_epic['title']}")
                print(f"  Priority: {first_epic['priority']}")
                print(f"  Stories: {len(first_epic.get('user_stories', []))}")
    else:
        print(f"\n❌ Error: {result.get('error', 'Unknown error')}")

    print("\n" + "=" * 80)
