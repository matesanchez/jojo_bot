"""
protocol_generator.py — Generate detailed purification protocols using Claude.
"""
import logging
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import settings, VALID_INSTRUMENTS
from rag.generator import _get_client, _collect_text
from rag.retriever import retrieve

logger = logging.getLogger(__name__)

PURIFICATION_TYPE_LABELS = {
    "affinity": "Affinity Chromatography (His-tag)",
    "affinity_gst": "Affinity Chromatography (GST-tag)",
    "ion_exchange": "Ion Exchange Chromatography",
    "size_exclusion": "Size Exclusion Chromatography",
    "hydrophobic": "Hydrophobic Interaction Chromatography",
    "mixed": "Mixed / Multi-step Purification",
}

VALID_PURIFICATION_TYPES = set(PURIFICATION_TYPE_LABELS.keys())


def _validate_instrument(instrument: str) -> str:
    """Validate instrument against whitelist; raise ValueError if invalid."""
    if instrument not in VALID_INSTRUMENTS:
        raise ValueError(
            f"Invalid instrument '{instrument}'. "
            f"Must be one of: {sorted(VALID_INSTRUMENTS)}"
        )
    return instrument


def _validate_purification_type(purification_type: str) -> str:
    """Validate purification_type against whitelist."""
    if purification_type not in VALID_PURIFICATION_TYPES:
        raise ValueError(
            f"Invalid purification_type '{purification_type}'. "
            f"Must be one of: {sorted(VALID_PURIFICATION_TYPES)}"
        )
    return purification_type


async def generate_protocol(
    target_protein: str,
    purification_type: str,
    instrument: str,
    column: str | None,
    sample_volume: str | None,
    additional_notes: str | None,
    history: list[dict],
) -> dict:
    """
    Generate a complete purification protocol using Claude, grounded in ÄKTA manual best practices.

    Returns:
        {"protocol_markdown": str, "protocol_title": str, "warnings": list[str]}
    """
    # --- Input validation ---
    instrument = _validate_instrument(instrument)
    purification_type = _validate_purification_type(purification_type)

    # Sanitise free-text fields — strip null bytes and limit length
    target_protein = target_protein.replace("\x00", "").strip()[:200]
    column = (column or "").replace("\x00", "").strip()[:100] or None
    sample_volume = (sample_volume or "").replace("\x00", "").strip()[:50] or None
    additional_notes = (additional_notes or "").replace("\x00", "").strip()[:500] or None

    if not target_protein:
        raise ValueError("target_protein cannot be empty.")

    # --- Retrieve relevant chunks ---
    search_query = (
        f"{purification_type} purification {target_protein} "
        f"{instrument} column equilibration gradient"
    )
    instrument_filter = instrument if instrument not in ("general",) else None
    chunks = retrieve(query=search_query, instrument_filter=instrument_filter, k=8)

    # --- Build context block ---
    context_lines: list[str] = []
    for i, chunk in enumerate(chunks, 1):
        title = chunk.get("doc_title", chunk.get("source_file", "Manual"))
        section = chunk.get("section", "")
        page = chunk.get("page", "")
        header = f"[{i}] {title}"
        if section:
            header += f", {section}"
        if page:
            header += f", p. {page}"
        context_lines.append(header)
        context_lines.append(f'"{chunk["text"]}"')
        context_lines.append("")
    context_block = "\n".join(context_lines)

    purification_label = PURIFICATION_TYPE_LABELS[purification_type]
    column_str = column or "to be selected"
    sample_volume_str = sample_volume or "not specified"
    notes_str = additional_notes or "none"

    prompt = f"""Generate a complete, detailed purification protocol with the following parameters:

**Target protein:** {target_protein}
**Purification method:** {purification_label}
**Instrument:** ÄKTA {instrument}
**Column:** {column_str}
**Sample volume:** {sample_volume_str}
**Additional notes:** {notes_str}

Ground the protocol in the ÄKTA manual documentation provided below. Use proper chromatography terminology and realistic parameter values.

RELEVANT MANUAL DOCUMENTATION:
{context_block}

Generate the protocol with ALL of the following sections in this exact order:

# [Protocol Title] — [Date: today]

## 1. Objective

## 2. Equipment & Materials
- Instrument
- Column
- Buffers required
- Additional equipment

## 3. Buffer Preparation
Include exact recipes with concentrations and pH.

## 4. System Preparation
Priming and equilibration steps with exact volumes (column volumes) and flow rates.

## 5. Sample Preparation

## 6. UNICORN Method Setup
Step-by-step instructions for setting up the method in UNICORN software.

## 7. Run Protocol
Detailed steps with flow rates (mL/min), volumes (CV), UV monitoring thresholds, fraction collection triggers.

## 8. Fraction Collection & Analysis
How to evaluate fractions, what SDS-PAGE or other analysis to run.

## 9. Column CIP & Storage
Cleaning-in-place procedure and storage conditions.

## 10. Safety Precautions
Any relevant safety warnings.

## 11. Troubleshooting Quick Reference
A table or list of common issues and fixes.

## 12. References
Which manuals and sections this protocol is based on.

Be specific and practical. Lab scientists should be able to follow this protocol step by step.
"""

    client = _get_client()

    try:
        response = await client.messages.create(
            model=settings.claude_model,
            max_tokens=4096,
            temperature=0.2,
            system=(
                "You are Jojo Bot, an expert in Cytiva ÄKTA chromatography systems. "
                "Generate detailed, accurate, step-by-step purification protocols grounded in official Cytiva documentation. "
                "Always include realistic flow rates, buffer volumes in column volumes (CV), "
                "and specific UNICORN software instructions."
            ),
            messages=[{"role": "user", "content": prompt}],
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
        )

        protocol_text = _collect_text(response.content)

        # Extract title from first heading
        title_match = re.search(r"^#\s+(.+?)(?:\s*—|\n)", protocol_text, re.MULTILINE)
        protocol_title = (
            title_match.group(1).strip()
            if title_match
            else f"{target_protein} Purification Protocol"
        )

        # Extract safety warnings
        warnings: list[str] = []
        safety_section = re.search(
            r"##\s+\d+\.\s+Safety Precautions\n(.*?)(?=\n##|\Z)", protocol_text, re.DOTALL
        )
        if safety_section:
            for line in safety_section.group(1).strip().splitlines():
                line = line.strip().lstrip("-•*").strip()
                if line:
                    warnings.append(line)

        return {
            "protocol_markdown": protocol_text,
            "protocol_title": protocol_title,
            "warnings": warnings[:5],
        }

    except ValueError:
        raise  # Let validation errors propagate as 400
    except Exception as e:
        logger.error(f"Protocol generation failed: {e}", exc_info=True)
        return {
            "protocol_markdown": "Protocol generation failed. Please try again.",
            "protocol_title": f"{target_protein} Purification Protocol",
            "warnings": [],
        }
