"""Constrained natural-language planner for supported After Effects actions.

This module deliberately uses local rules only: it does not execute scripts, call an
LLM, or accept arbitrary ExtendScript. Every plan maps to an explicit allowlisted action.
"""
import re

SUPPORTED_ACTIONS = {"animated_text", "shape", "liquid_glass", "organize"}
DEFAULTS = {"text": "VASTOCHNIY", "prefix": "AI — ", "duration": 0.8}


class PlanningError(ValueError):
    """Raised when a request cannot be mapped safely to a supported action."""


def plan_request(prompt):
    if not isinstance(prompt, str) or not prompt.strip():
        raise PlanningError("Describe the After Effects action you want.")
    if len(prompt) > 1000:
        raise PlanningError("Keep the request under 1,000 characters.")

    source = prompt.strip()
    normalized = source.lower()
    params = dict(DEFAULTS)

    duration_match = re.search(r"\b(?:in|over|duration(?: of)?)\s*(\d+(?:\.\d+)?)\s*(?:s|sec|secs|seconds?)\b", normalized)
    if duration_match:
        params["duration"] = max(0.2, min(5.0, float(duration_match.group(1))))

    quoted = re.search(r"""["'“”‘’](.+?)["'“”‘’]""", source)
    text_match = re.search(r"\b(?:saying|text(?: that says)?|with the text)\s*[:=]?\s*(.+?)(?:\s+in\s+\d+(?:\.\d+)?\s*(?:s|sec|secs|seconds?)\b|$)", source, re.I)
    if quoted:
        params["text"] = quoted.group(1).strip()[:180]
    elif text_match:
        params["text"] = text_match.group(1).strip(" .,!")[:180]

    prefix_match = re.search(r"""\bprefix\b.*?\bwith\s+["'“”‘’]?(.+?)["'“”‘’]?$""", source, re.I)
    if prefix_match:
        params["prefix"] = prefix_match.group(1).strip(" .,!" + chr(34) + "'“”‘’")[:40] or DEFAULTS["prefix"]

    if any(word in normalized for word in ("rename", "prefix", "organize layer", "organise layer")):
        action = "organize"
        explanation = "Prefix the currently selected layers. Select the target layers in After Effects before running."
    elif any(phrase in normalized for phrase in ("liquid glass", "glass effect", "glass starter", "translucent glass")):
        action = "liquid_glass"
        explanation = "Create the existing translucent-fill/highlight-stroke glass starter. It does not simulate physical refraction."
    elif any(phrase in normalized for phrase in ("rounded rectangle", "rectangle shape", "shape layer", "create a shape", "make a shape")):
        action = "shape"
        explanation = "Create the existing rounded-rectangle shape layer in the active composition."
    elif any(phrase in normalized for phrase in ("animated text", "kinetic typography", "text layer", "text saying", "text that says", "add text", "create text", "make text", "title saying")):
        action = "animated_text"
        explanation = "Create a text layer with the existing scale/opacity entrance animation."
    else:
        raise PlanningError(
            "I couldn't map that request to a supported action. Try: "
            "'Create animated text saying Hello in 1.2 seconds', "
            "'Create a rounded rectangle', 'Create a liquid glass starter', or "
            "'Prefix selected layers with BG'."
        )

    if action not in SUPPORTED_ACTIONS:
        raise PlanningError("The requested action is not allowlisted.")
    return {
        "action": action,
        "text": params["text"],
        "prefix": params["prefix"],
        "duration": params["duration"],
        "explanation": explanation,
        "requires_confirmation": True,
    }
