#!/usr/bin/env python3
"""Local Streamlit interface for manually annotating SmPCs with ontology.py."""
from __future__ import annotations

from dataclasses import MISSING, asdict, fields, is_dataclass
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
import types
from typing import Any, get_args, get_origin, get_type_hints

import ontology
from parse_package_inserts import DATASET_ID, parse_smpc

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output" / "manual-annotations"
IDENTITY_FIELDS = {
    "1": ("name",),
    "2": ("substances",),
    "3": ("description", "pharmaceutical_form"),
    "7": ("manufacturer", "marketing_authorisation_holder"),
}
SECTION_TYPES = {
    "4.1": ("indications", ontology.Indication),
    "4.2": ("dosage", ontology.DoseRecommendation),
    "4.3": ("contraindications", ontology.Contraindication),
    "4.4": ("warnings", ontology.Warning),
    "4.5": ("interactions", ontology.Interaction),
    "4.6": ("warnings", ontology.Warning),
    "4.7": ("warnings", ontology.Warning),
    "4.8": ("adverse_reactions", ontology.AdverseReaction),
    "4.9": ("overdose", ontology.Overdose),
    "5.1": ("pharmacodynamics", ontology.Pharmacodynamics),
    "5.2": ("pharmacokinetics", ontology.Pharmacokinetics),
    "5.3": ("preclinical_safety", ontology.PreclinicalSafety),
}
LONG_FIELDS = {
    "summary", "description", "effect", "clinical_consequence", "recommendation",
    "adjustment", "administration_instructions", "management", "reported_cases",
    "mechanism_of_action", "clinical_efficacy_and_safety", "absorption", "distribution",
    "metabolism", "elimination", "pharmacokinetic_properties", "special_populations",
    "findings", "safety_pharmacology", "toxicology", "genotoxicity", "carcinogenicity",
    "reproductive_and_developmental_toxicity", "applicability", "conditions", "risk",
    "manifestations", "pharmacodynamic_effects", "conditions", "populations",
}


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def encoded(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def source_id(record_id: str, language: str, text: str, document_index: int) -> str:
    return f"{record_id}|{language}|{digest(text)}|smpc:{document_index}"


def section_id(section: dict) -> str:
    return f"smpc:{section['document_index']}:{section['number'] or 'introduction'}@{section['start']}"


def safe_name(name: str) -> str:
    return re.sub(r"[^\w.-]+", "_", name, flags=re.UNICODE).strip("_.")[:80] or "document"


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def annotation_paths(metadata: dict) -> tuple[Path, Path]:
    token = digest(encoded([metadata["record_id"], metadata["source_sha256"],
                            metadata["language"], metadata["document_index"]]))[:20]
    base = OUTPUT / metadata["language"] / metadata["split"] / f"{safe_name(metadata['record_name'])}-{token}"
    return base.with_suffix(".draft.json"), base.with_suffix(".json")


def render_dataclass(st, cls: type, prefix: str, initial: dict | None = None) -> dict:
    """Render ontology fields recursively, keeping evidence controlled by the source UI."""
    initial = initial or {}
    values = {}
    for field in fields(cls):
        name = field.name
        if name in {"evidence", "id"}:
            continue
        tp = get_type_hints(cls)[name]
        origin, args = get_origin(tp), get_args(tp)
        optional = origin is types.UnionType and type(None) in args
        value_type = next((arg for arg in args if arg is not type(None)), None) if optional else tp
        value = initial.get(name)
        label = name.replace("_", " ").capitalize()
        key = f"{prefix}.{name}"

        if value_type is str:
            default = value if isinstance(value, str) else ""
            if name == "severity":
                values[name] = st.text_input(label, value=default, key=key) or None
            elif name in LONG_FIELDS or len(default) > 90:
                entered = st.text_area(label, value=default, key=key, height=90)
                values[name] = entered or (None if optional else "")
            else:
                entered = st.text_input(label, value=default, key=key)
                values[name] = entered or (None if optional else "")
        elif value_type is int:
            values[name] = st.number_input(label, value=int(value or 0), step=1, key=key)
        elif get_origin(value_type) is list:
            item_type = get_args(value_type)[0]
            items = value if isinstance(value, list) else []
            if item_type is str:
                text = "\n".join(str(item) for item in items)
                entered = st.text_area(f"{label} (one item per line)", value=text, key=key, height=90)
                parsed = [line.strip() for line in entered.splitlines() if line.strip()]
                values[name] = parsed or (None if optional else [])
            elif is_dataclass(item_type):
                count = st.number_input(f"{label} count", min_value=0, max_value=30,
                                        value=len(items), step=1, key=f"{key}.count")
                nested = []
                for index in range(int(count)):
                    with st.expander(f"{label[:-1] if label.endswith('s') else label} {index + 1}",
                                     expanded=True):
                        nested.append(render_dataclass(st, item_type, f"{key}.{index}",
                                                       items[index] if index < len(items) else None))
                values[name] = nested or (None if optional else [])
        elif is_dataclass(value_type):
            include = st.checkbox(f"Include {label.lower()}", value=value is not None,
                                  key=f"{key}.include")
            if include:
                values[name] = render_dataclass(st, value_type, key, value if isinstance(value, dict) else None)
            else:
                values[name] = None
    return values


def evidence_for(excerpt: str, section: dict, metadata: dict, occurrence: int) -> dict | None:
    if not excerpt.strip():
        return None
    text = section["text"]
    starts, cursor = [], 0
    while True:
        position = text.find(excerpt, cursor)
        if position < 0:
            break
        starts.append(position)
        cursor = position + 1
    is_exact = bool(starts)
    start = section["start"] + starts[min(occurrence, len(starts) - 1)] if is_exact else None
    return {
        "source_id": metadata["source_id"], "document_title": metadata["record_name"],
        "section_title": section["title"], "section_id": section_id(section),
        "exact_text": excerpt, "span_start": start,
        "span_end": start + len(excerpt) if is_exact else None,
        "language": metadata["language"], "is_exact": is_exact,
    }


@lru_cache(maxsize=3)
def load_records(split: str):
    from datasets import load_dataset
    return load_dataset(DATASET_ID, split=split)


@lru_cache(maxsize=2)
def parse_document(text: str, language: str) -> dict:
    return parse_smpc(text, language)


def identity_editor(st, field_name: str, initial: Any, prefix: str) -> Any:
    label = field_name.replace("_", " ").capitalize()
    if field_name == "substances":
        text = "\n".join(initial if isinstance(initial, list) else [])
        return [line.strip() for line in st.text_area(f"{label} (one per line)", value=text,
                                                       key=prefix).splitlines() if line.strip()]
    return st.text_area(label, value=initial or "", key=prefix, height=90) or None


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="SmPC annotation", layout="wide")
    st.title("Manual SmPC annotation")
    st.caption("Create source-supported annotations using the dataclasses in ontology.py.")
    split = st.sidebar.selectbox("Dataset split", ("train", "validation", "test"))
    language = st.sidebar.selectbox("Language", ("sk", "en"))
    try:
        records = load_records(split)
    except Exception as exc:
        st.error(f"Could not load {DATASET_ID} ({split}): {exc}")
        st.info("The first launch may need network access to download the dataset into the Hugging Face cache.")
        return
    eligible_indexes = [index for index in range(len(records))
                        if isinstance(records[index].get(language), str)
                        and records[index][language].strip()]
    if not eligible_indexes:
        st.warning(f"No records with {language} source text were found in this split.")
        return
    record_labels = {index: f"{records[index].get('name') or 'unnamed'} · record {index}"
                     for index in eligible_indexes}
    record_index = st.sidebar.selectbox("Product record", eligible_indexes,
                                        format_func=lambda value: record_labels[value])
    record = dict(records[record_index])
    raw_text = record[language]
    parsed = parse_document(raw_text, language)
    documents = sorted({section["document_index"] for section in parsed["sections"]
                        if section["number"] is not None})
    if not documents:
        st.warning("No recognizable SmPC sections were detected in this record.")
        return
    doc_index = st.sidebar.selectbox("SmPC document", documents)
    selected_sections = [section for section in parsed["sections"]
                         if section["document_index"] == doc_index]
    record_id = str(record.get("document_id") or record.get("id") or record.get("name") or f"record-{record_index}")
    metadata = {
        "source_id": source_id(record_id, language, raw_text, doc_index),
        "record_id": record_id, "record_name": str(record.get("name") or f"record-{record_index}"),
        "input_source": DATASET_ID, "split": split, "source_sha256": digest(raw_text),
        "language": language, "document_index": doc_index,
        "start": selected_sections[0]["start"], "end": selected_sections[-1]["end"],
    }
    draft_path, product_path = annotation_paths(metadata)
    draft = {"metadata": metadata, "annotations": {}, "completed_sections": []}
    if draft_path.exists():
        try:
            saved = json.loads(draft_path.read_text(encoding="utf-8"))
            if saved.get("metadata", {}).get("source_sha256") == metadata["source_sha256"]:
                draft = saved
        except (OSError, json.JSONDecodeError):
            st.warning("The saved draft could not be read; a new draft will be created.")

    section_options = list(range(len(selected_sections)))
    section_labels = [f"{section['number'] or 'Introduction'} · {section['title']}"
                      for section in selected_sections]
    selected_index = st.sidebar.selectbox("Section", section_options,
        format_func=lambda value: ("✓ " if section_id(selected_sections[value]) in draft["completed_sections"] else "○ ")
                                  + section_labels[value])
    section = selected_sections[selected_index]
    identifier = section_id(section)
    st.subheader(section_labels[selected_index])
    if parsed["warnings"]:
        with st.expander("Parser warnings", expanded=False):
            for warning in parsed["warnings"]:
                st.write(warning)
    with st.expander("Original source section", expanded=True):
        st.text(section["text"])

    number = section["number"]
    existing = draft["annotations"].get(identifier, [])
    kind_info = SECTION_TYPES.get(number)
    identity_fields = IDENTITY_FIELDS.get(number, ())
    if not kind_info and not identity_fields:
        st.info("This section has no corresponding fields in ontology.py. Mark it reviewed to continue.")
        if st.button("Mark section reviewed", key=f"review.{identifier}"):
            if identifier not in draft["completed_sections"]:
                draft["completed_sections"].append(identifier)
            draft["annotations"].setdefault(identifier, [])
            atomic_json(draft_path, draft)
            st.success(f"Draft saved to {draft_path.relative_to(ROOT)}")
        entries = []
    elif identity_fields:
        with st.form(f"identity.{identifier}"):
            entries = []
            for field_name in identity_fields:
                old = next((item for item in existing if item.get("field") == field_name), {})
                current = old.get("data", {}).get(field_name)
                value = identity_editor(st, field_name, current, f"identity.{identifier}.{field_name}")
                label = field_name.replace("_", " ").capitalize()
                excerpt = st.text_area(f"{label} evidence excerpt",
                                       value=old.get("excerpt", ""),
                                       key=f"identity.{identifier}.{field_name}.evidence")
                matches = section["text"].count(excerpt) if excerpt else 0
                occurrence = 0
                if matches > 1:
                    occurrence = st.selectbox("Matching occurrence in this section", range(matches),
                                              index=min(old.get("occurrence", 0), matches - 1),
                                              key=f"identity.{identifier}.{field_name}.occurrence")
                if excerpt:
                    st.caption("Exact source match" if matches else "Excerpt not found verbatim; it will be saved as inexact evidence.")
                entries.append({"data": {field_name: value}, "excerpt": excerpt,
                                "occurrence": occurrence, "field": field_name})
            complete = st.checkbox("Section reviewed", value=identifier in draft["completed_sections"],
                                   key=f"identity.{identifier}.complete")
            submitted = st.form_submit_button("Save section")
        if submitted:
            # Each identity attribute is stored independently with its own excerpt.
            draft["annotations"][identifier] = entries
            if complete and identifier not in draft["completed_sections"]:
                draft["completed_sections"].append(identifier)
            elif not complete:
                draft["completed_sections"] = [item for item in draft["completed_sections"] if item != identifier]
            atomic_json(draft_path, draft)
            st.success(f"Draft saved to {draft_path.relative_to(ROOT)}")
    else:
        collection, annotation_type = kind_info
        with st.form(f"facts.{identifier}"):
            count = st.number_input("Number of facts in this section", min_value=0, max_value=50,
                                    value=len(existing), step=1, key=f"facts.{identifier}.count")
            entries = []
            for index in range(int(count)):
                prior = existing[index] if index < len(existing) else {}
                with st.expander(f"{annotation_type.__name__} {index + 1}", expanded=True):
                    data = render_dataclass(st, annotation_type, f"{identifier}.{index}", prior.get("data"))
                    excerpt = st.text_area("Verbatim evidence excerpt", value=prior.get("excerpt", ""),
                                           key=f"{identifier}.{index}.evidence", height=90)
                    occurrence_count = section["text"].count(excerpt) if excerpt else 0
                    if occurrence_count > 1:
                        occurrence = st.selectbox("Matching occurrence in this section", range(occurrence_count),
                                                  index=min(prior.get("occurrence", 0), occurrence_count - 1),
                                                  key=f"{identifier}.{index}.occurrence")
                    else:
                        occurrence = 0
                    if excerpt:
                        st.caption("Exact source match" if occurrence_count else "Excerpt not found verbatim; it will be saved as inexact evidence.")
                    entries.append({"data": data, "excerpt": excerpt, "occurrence": occurrence})
            complete = st.checkbox("Section reviewed", value=identifier in draft["completed_sections"],
                                   key=f"facts.{identifier}.complete")
            submitted = st.form_submit_button("Save section")
        if submitted:
            draft["annotations"][identifier] = entries
            if complete and identifier not in draft["completed_sections"]:
                draft["completed_sections"].append(identifier)
            elif not complete:
                draft["completed_sections"] = [item for item in draft["completed_sections"] if item != identifier]
            atomic_json(draft_path, draft)
            st.success(f"Draft saved to {draft_path.relative_to(ROOT)}")

    # Assemble the export from all section drafts, retaining each evidence excerpt.
    product: dict[str, Any] = {"id": metadata["source_id"], "name": ""}
    for name in ("manufacturer", "description", "pharmaceutical_form", "marketing_authorisation_holder"):
        product[name] = None
    product.update({key: [] for key in (
        "substances", "indications", "contraindications", "interactions", "dosage", "warnings",
        "adverse_reactions", "overdose", "pharmacodynamics", "pharmacokinetics", "preclinical_safety")})
    product["identity_evidence"] = {}
    for source_section in selected_sections:
        sid = section_id(source_section)
        for entry in draft["annotations"].get(sid, []):
            evidence = evidence_for(entry.get("excerpt", ""), source_section, metadata,
                                    int(entry.get("occurrence", 0)))
            if entry.get("field"):
                field_name = entry["field"]
                value = entry["data"].get(field_name)
                if value is not None:
                    if field_name == "name":
                        product["name"] = value
                    elif field_name == "substances":
                        product["substances"] = value
                    else:
                        product[field_name] = value
                if evidence:
                    product["identity_evidence"].setdefault(field_name, []).append(evidence)
            else:
                collection = SECTION_TYPES.get(source_section["number"], (None, None))[0]
                if not collection:
                    continue
                fact = dict(entry.get("data", {}))
                if issubclass(SECTION_TYPES[source_section["number"]][1], ontology.Statement):
                    fact["evidence"] = [evidence] if evidence else None
                product[collection].append(fact)
    st.divider()
    st.write(f"Reviewed sections: {len(draft['completed_sections'])} / {len(selected_sections)}")
    st.caption(f"Working draft: `{draft_path.relative_to(ROOT)}`")
    if st.button("Export Product JSON", type="primary", disabled=not product["name"]):
        # Build and serialize through the ontology to catch invalid required values.
        try:
            product_obj = materialize(product, ontology.Product)
            if not product_obj.name.strip():
                st.error("Enter a product name in section 1 before exporting.")
            else:
                atomic_json(product_path, asdict(product_obj))
                st.success(f"Product JSON exported to {product_path.relative_to(ROOT)}")
                st.download_button("Download Product JSON", data=product_path.read_text(encoding="utf-8"),
                                   file_name=product_path.name, mime="application/json")
        except (TypeError, ValueError) as exc:
            st.error(f"The annotation is incomplete or invalid: {exc}")


def materialize(value: Any, tp: Any) -> Any:
    """Convert nested form dictionaries to the ontology's actual dataclasses."""
    origin, args = get_origin(tp), get_args(tp)
    if origin is types.UnionType:
        if value is None and type(None) in args:
            return None
        target = next(arg for arg in args if arg is not type(None))
        return materialize(value, target)
    if origin is list:
        if value is None:
            return None
        return [materialize(item, args[0]) for item in value]
    if origin is dict:
        if value is None:
            return None
        return {materialize(key, args[0]): materialize(item, args[1])
                for key, item in value.items()}
    if is_dataclass(tp):
        if not isinstance(value, dict):
            raise TypeError(f"Expected an object for {tp.__name__}")
        hints = get_type_hints(tp)
        converted = {key: materialize(item, hints[key]) for key, item in value.items()
                     if key in hints}
        for field in fields(tp):
            if field.name not in converted and field.default is field.default_factory is MISSING:
                raise ValueError(f"{tp.__name__}.{field.name} is required")
        for field_name, field_type in hints.items():
            if field_type is str and not converted.get(field_name, "").strip():
                raise ValueError(f"{tp.__name__}.{field_name} is required")
        result = tp(**converted)
        if isinstance(result, (ontology.Indication, ontology.Contraindication)) and not result.conditions:
            raise ValueError(f"{tp.__name__}.conditions must contain at least one item")
        return result
    return value


if __name__ == "__main__":
    main()
