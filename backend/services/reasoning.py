"""LLM reasoning service for disaster response recommendations."""

import asyncio
import json
import logging
import re
from typing import Dict, List, Any

from models.models import CommunityKnowledge, CommunityAsset, CommunityEvent
from services.retrieval import RetrievalResult
from llm_client import llm

logger = logging.getLogger(__name__)

# Configuration
MAX_CONTEXT_CHARS = 8000  # Approximate token limit safety margin
MAX_RETRIES = 2
TIMEOUT_SECONDS = 120


def format_knowledge_context(entries: List[CommunityKnowledge]) -> str:
    """Format knowledge entries for the prompt."""
    if not entries:
        return "No relevant community knowledge found."

    blocks = []
    for e in entries:
        tags_str = ", ".join(e.tags) if e.tags else "none"
        block = f"""[Knowledge #{e.id}]
Title: {e.title}
Description: {e.description}
Location: {e.location or 'not specified'}
Hazard Type: {e.hazard_type or 'general'}
Tags: {tags_str}
Source: {e.source or 'community'}"""
        blocks.append(block)

    return "\n\n".join(blocks)


def format_asset_context(assets: List[CommunityAsset]) -> str:
    """Format asset entries for the prompt."""
    if not assets:
        return ""

    blocks = []
    for a in assets:
        tags_str = ", ".join(a.tags) if a.tags else "none"
        block = f"""[Asset: {a.name}]
Type: {a.asset_type}
Description: {a.description or 'no description'}
Location: {a.location or 'not specified'}
Capacity: {a.capacity or 'unknown'}
Status: {a.status or 'unknown'}
Tags: {tags_str}"""
        blocks.append(block)

    return "\n\n".join(blocks)


def format_event_context(events: List[CommunityEvent]) -> str:
    """Format event entries for the prompt."""
    if not events:
        return ""

    blocks = []
    for e in events:
        block = f"""[Historical Event]
Type: {e.event_type}
Description: {e.description}
Location: {e.location or 'not specified'}
Severity: {e.severity or 'unknown'}/5
Reported by: {e.reported_by or 'community member'}"""
        blocks.append(block)

    return "\n\n".join(blocks)


def format_full_context(result: RetrievalResult) -> str:
    """Combine all context into a single formatted string."""
    sections = []

    knowledge_context = format_knowledge_context(result.knowledge)
    sections.append(f"### Community Knowledge\n{knowledge_context}")

    if result.assets:
        asset_context = format_asset_context(result.assets)
        sections.append(f"### Community Assets\n{asset_context}")

    if result.events:
        event_context = format_event_context(result.events)
        sections.append(f"### Recent/Historical Events\n{event_context}")

    return "\n\n".join(sections)


def truncate_context(context: str, max_chars: int) -> str:
    """Truncate context to fit within limits, preserving complete sections."""
    if len(context) <= max_chars:
        return context

    # Try to preserve complete entries by splitting on double newlines
    entries = context.split("\n\n")
    truncated = []
    current_length = 0

    for entry in entries:
        if current_length + len(entry) + 2 > max_chars:
            break
        truncated.append(entry)
        current_length += len(entry) + 2

    result = "\n\n".join(truncated)
    logger.warning(f"Context truncated from {len(context)} to {len(result)} chars")
    return result


def build_prompt(user_input: str, context: str) -> str:
    """Build the full reasoning prompt."""
    return f"""You are a disaster response reasoning assistant. You use community knowledge to help coordinators make safe, equitable, and context-aware decisions.

Your goals:
1. Understand the situation described by the user.
2. Use the provided community knowledge to ground your reasoning.
3. Produce a clear, concise situation summary.
4. Recommend 3-5 prioritized actions.
5. Provide a short rationale for each action.
6. NEVER hallucinate facts not supported by the context.

---

## Community Context

The following information comes from local community knowledge. Use it carefully:

{context}

---

## Current Situation

{user_input}

---

## Output Format

Respond ONLY with a valid JSON object in this exact structure:

{{
  "summary": "One-paragraph summary of the situation and key concerns.",
  "actions": [
    {{
      "priority": 1,
      "action": "First recommended action.",
      "rationale": "Why this action matters, referencing community knowledge."
    }},
    {{
      "priority": 2,
      "action": "Second recommended action.",
      "rationale": "Why this action matters."
    }},
    {{
      "priority": 3,
      "action": "Third recommended action.",
      "rationale": "Why this action matters."
    }}
  ]
}}

Important:
- Include 3-5 actions, prioritized by urgency and impact
- Reference specific community knowledge when relevant
- Focus on safety, vulnerable populations, and practical next steps
- Do not include any text outside the JSON object
"""


def parse_response(response: str) -> Dict[str, Any]:
    """Parse LLM response with fallback handling."""
    # First, try direct JSON parse
    try:
        data = json.loads(response)
        return validate_response(data)
    except json.JSONDecodeError:
        pass

    # Try to extract JSON from response (model may include extra text)
    json_match = re.search(r'\{[\s\S]*\}', response)
    if json_match:
        try:
            data = json.loads(json_match.group())
            return validate_response(data)
        except json.JSONDecodeError:
            pass

    # Fallback: return error response
    logger.error(f"Failed to parse LLM response: {response[:200]}...")
    return error_response("Unable to parse the model's response.")


def validate_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and normalize the response structure."""
    if "summary" not in data:
        data["summary"] = "Response received but summary was missing."

    if "actions" not in data or not isinstance(data["actions"], list):
        data["actions"] = []

    # Ensure each action has required fields
    for i, action in enumerate(data["actions"]):
        if "priority" not in action:
            action["priority"] = i + 1
        if "action" not in action:
            action["action"] = "Action details missing"
        if "rationale" not in action:
            action["rationale"] = "No rationale provided"

    return data


def error_response(message: str) -> Dict[str, Any]:
    """Return a structured error response."""
    return {
        "summary": message,
        "actions": [],
        "error": True
    }


async def run_reasoning_model(
    user_input: str,
    context: RetrievalResult,
) -> Dict[str, Any]:
    """
    Main reasoning function with error handling and retries.

    Args:
        user_input: The user's situation description
        context: Retrieved context from the database

    Returns:
        Dict containing summary and prioritized actions
    """
    # Format context
    context_text = format_full_context(context)

    # Truncate if too long
    if len(context_text) > MAX_CONTEXT_CHARS:
        context_text = truncate_context(context_text, MAX_CONTEXT_CHARS)

    # Build prompt
    prompt = build_prompt(user_input, context_text)
    logger.debug(f"Prompt length: {len(prompt)} chars")

    # Try with retries
    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            logger.info(f"Calling LLM (attempt {attempt + 1}/{MAX_RETRIES + 1})")

            response = await asyncio.wait_for(
                llm.generate(prompt),
                timeout=TIMEOUT_SECONDS
            )

            result = parse_response(response)

            if "error" not in result:
                logger.info("LLM reasoning completed successfully")
                return result

        except asyncio.TimeoutError:
            last_error = "timeout"
            logger.warning(f"LLM timeout on attempt {attempt + 1}")

        except Exception as e:
            last_error = str(e)
            logger.error(f"LLM error on attempt {attempt + 1}: {e}")

    # All retries failed
    if last_error == "timeout":
        return error_response(
            "The system is taking too long to respond. Please try again."
        )
    else:
        return error_response(
            f"Unable to generate recommendations. Error: {last_error}"
        )
