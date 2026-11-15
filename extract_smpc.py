#!/usr/bin/env python3
"""Extract ontology-based information from SmPC sections without a graph DB."""
from __future__ import annotations

import argparse
from dataclasses import MISSING, asdict, fields, is_dataclass
from functools import lru_cache
import hashlib
from itertools import islice
import json
import os
from pathlib import Path
import re
import sys
import types
from typing import Any, get_args, get_origin, get_type_hints
import unicodedata

import ontology
from parse_package_inserts import DATASET_ID, fold, parse_smpc, records_from

ROOT = Path(__file__).resolve().parent
PROMPTS = ('smpc-extract.txt', 'smpc-identity.txt', 'smpc-clinical.txt', 'smpc-other.txt')
IDENTITY = ('name', 'manufacturer', 'substances', 'description',
            'pharmaceutical_form', 'marketing_authorisation_holder')
COLLECTIONS = ('substances', 'indications', 'contraindications', 'interactions',
               'dosage', 'warnings', 'adverse_reactions')
VERSION = 1


def digest(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def encoded(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


@lru_cache(maxsize=None)
def hints(cls: type) -> dict:
    return get_type_hints(cls)


def response_schema(tp: Any) -> dict:
    """Derive the response contract from the actual ontology, not a second model."""
    origin, args = get_origin(tp), get_args(tp)
    if origin is types.UnionType:
        return {'anyOf': [response_schema(arg) for arg in args]}
    if tp is type(None):
        return {'type': 'null'}
    if tp is str:
        return {'type': 'string', 'minLength': 1}
    if tp is int:
        return {'type': 'integer'}
    if origin is list:
        return {'type': 'array', 'items': response_schema(args[0])}
    if origin is dict:
        # Product.identity_evidence is the ontology's only dictionary field.
        return {'type': 'object', 'properties': {
            key: response_schema(args[1]) for key in IDENTITY},
            'additionalProperties': False}
    if tp is ontology.Evidence:
        return {'anyOf': [
            {'type': 'null'},
            {'type': 'object', 'properties': {
                'exact_text': {'anyOf': [{'type': 'string'}, {'type': 'null'}]}},
             'required': [], 'additionalProperties': False}]}
    if is_dataclass(tp):
        attributes = [f for f in fields(tp) if not (tp is ontology.Product and f.name == 'id')]
        return {'type': 'object', 'properties': {
            f.name: response_schema(hints(tp)[f.name]) for f in attributes},
            'required': [] if tp is ontology.Product else [
                f.name for f in attributes
                if f.default is MISSING and f.default_factory is MISSING],
            'additionalProperties': False}
    raise TypeError(f'Unsupported ontology type: {tp}')


def clean_string(value: str) -> str:
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', value)).strip()


def fact_key(value: Any) -> str:
    def without_evidence(item):
        if isinstance(item, dict):
            return {k: without_evidence(v) for k, v in item.items() if k != 'evidence'}
        if isinstance(item, list):
            return [without_evidence(v) for v in item]
        return item
    return encoded(without_evidence(value))


def merge_duplicates(items: list) -> list:
    result, positions = [], {}
    for item in items:
        key = fact_key(item)
        if key not in positions:
            positions[key] = len(result)
            result.append(item)
        else:
            result[positions[key]] = combine(result[positions[key]], item)
    return result


def combine(left: Any, right: Any) -> Any:
    """Merge provenance recursively only for otherwise identical facts."""
    if left is None:
        return right
    if right is None:
        return left
    if isinstance(left, list):
        return merge_duplicates(left + right)
    if isinstance(left, dict):
        return {key: combine(value, right[key]) for key, value in left.items()}
    return left


def normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: v if k == 'exact_text' else normalize(v) for k, v in value.items()}
    if isinstance(value, list):
        return merge_duplicates([normalize(item) for item in value])
    return clean_string(value) if isinstance(value, str) else value


def validate_value(value: Any, tp: Any, *, section: dict, metadata: dict,
                   path: str = 'response') -> Any:
    """Validate and materialize nested dataclasses, supplying evidence metadata."""
    origin, args = get_origin(tp), get_args(tp)
    if origin is types.UnionType:
        if value is None and type(None) in args:
            return None
        return validate_value(value, next(a for a in args if a is not type(None)),
                              section=section, metadata=metadata, path=path)
    if tp is str:
        if not isinstance(value, str) or not clean_string(value):
            raise ValueError(f'{path}: expected a nonempty string')
        return value
    if origin is list:
        if not isinstance(value, list):
            raise ValueError(f'{path}: expected an array')
        converted = [validate_value(v, args[0], section=section, metadata=metadata,
                                    path=f'{path}[{i}]') for i, v in enumerate(value)]
        if args[0] is ontology.Evidence:
            return [v for v in converted if v is not None] or None
        if args[0] is ontology.Population and any(v is None for v in converted):
            return [v for v in converted if v is not None] or None
        return converted
    if origin is dict:
        if not isinstance(value, dict) or set(value) - set(IDENTITY):
            raise ValueError(f'{path}: expected identity field evidence')
        return {k: validate_value(v, args[1], section=section, metadata=metadata,
                                   path=f'{path}.{k}') for k, v in value.items()}
    if tp is ontology.Evidence:
        if value is None:
            return None
        if not isinstance(value, dict) or set(value) - {'exact_text'}:
            raise ValueError(f'{path}: evidence must contain only exact_text')
        quote = value.get('exact_text')
        if quote is None:
            return None
        if not isinstance(quote, str):
            raise ValueError(f'{path}: evidence excerpt must be a string')
        if not quote.strip():
            return None
        position = section['text'].find(quote)
        is_exact = position >= 0
        start = section['start'] + position if is_exact else None
        return ontology.Evidence(
            source_id=metadata['source_id'], document_title=metadata['record_name'],
            section_title=section['title'], section_id=section['section_id'],
            exact_text=quote, span_start=start,
            span_end=start + len(quote) if is_exact else None,
            language=metadata['language'], is_exact=is_exact)
    if is_dataclass(tp):
        if not isinstance(value, dict):
            raise ValueError(f'{path}: expected an object')
        allowed = {f.name for f in fields(tp)}
        if set(value) - allowed:
            raise ValueError(f'{path}: unexpected fields {sorted(set(value) - allowed)}')
        converted = {k: validate_value(v, hints(tp)[k], section=section,
                                       metadata=metadata, path=f'{path}.{k}')
                     for k, v in value.items()}
        try:
            instance = tp(**converted)
        except TypeError as exc:
            missing = {f.name for f in fields(tp)
                       if f.default is MISSING and f.default_factory is MISSING
                       and f.name not in converted}
            if tp is ontology.Population and missing == {'name'}:
                return None
            raise ValueError(f'{path}: {exc}') from exc
        if isinstance(instance, (ontology.Indication, ontology.Contraindication)) and not instance.conditions:
            raise ValueError(f'{path}: conditions must not be empty')
        return instance
    raise TypeError(f'Unsupported ontology type at {path}: {tp}')


def validate_extraction(value: Any, section: dict, metadata: dict) -> dict:
    if not isinstance(value, dict):
        raise ValueError('Expected a partial Product JSON object')
    allowed = set(hints(ontology.Product)) - {'id'}
    if set(value) - allowed:
        raise ValueError(f'Unexpected Product fields: {sorted(set(value) - allowed)}')
    result = {}
    for key, item in value.items():
        # Product.name is required only after document aggregation.
        converted = validate_value(item, hints(ontology.Product)[key], section=section,
                                   metadata=metadata, path=key)
        result[key] = converted
    evidence = result.get('identity_evidence', {})
    for key, excerpts in evidence.items():
        if excerpts and not result.get(key):
            raise ValueError(f'{key}: identity evidence has no corresponding value')

    def serialize(item):
        if is_dataclass(item):
            return asdict(item)
        if isinstance(item, list):
            return [serialize(v) for v in item]
        if isinstance(item, dict):
            return {k: serialize(v) for k, v in item.items()}
        return item
    return normalize(serialize(result))


def section_guidance(section: dict, template: str) -> str:
    title = fold(section['title'])
    if template == 'human':
        if section['number'] in {'1', '2', '3', '7'}:
            return 'smpc-identity.txt'
        if section['number'] in {f'4.{i}' for i in range(1, 9)}:
            return 'smpc-clinical.txt'
        return 'smpc-other.txt'
    # Veterinary templates use different numbering. Match meaning instead.
    if re.search(r'name of|nazov|composition|zlozenie|pharmaceutical form|liekova forma|'
                 r'authorisation holder|drzitel|manufacturer|vyrobca', title):
        return 'smpc-identity.txt'
    if re.search(r'indication|indikaci|posology|dosage|davkov|administration|podav|'
                 r'contraindication|kontraindik|warning|upozornen|precaution|opatren|'
                 r'interaction|interakci|pregnan|gravid|lactat|laktaci|fertil|'
                 r'driv|vozidl|undesirable|neziaduc|adverse', title):
        return 'smpc-clinical.txt'
    return 'smpc-other.txt'


def extract_section(client: Any, model: str, prompts: dict, section: dict,
                    metadata: dict, template: str) -> dict:
    guidance = section_guidance(section, template)
    system = prompts['smpc-extract.txt'] + '\n\n' + prompts[guidance]
    user = {'record_name': metadata['record_name'], 'language': metadata['language'],
            'source_id': metadata['source_id'], 'template': template,
            'section_id': section['section_id'], 'section_title': section['title'],
            'source_start': section['start'], 'source_end': section['end'],
            'response_schema': response_schema(ontology.Product),
            'source_section': section['text']}
    response = client.chat.completions.create(
        model=model, messages=[{'role': 'system', 'content': system},
                               {'role': 'user', 'content': encoded(user)}],
        response_format={'type': 'json_object'})
    choice = response.choices[0]
    if getattr(choice, 'finish_reason', None) not in (None, 'stop'):
        raise ValueError(f'Incomplete model response: {choice.finish_reason}')
    content = choice.message.content
    if not isinstance(content, str) or not content.strip():
        raise ValueError('Empty model response')
    return validate_extraction(json.loads(content), section, metadata)


def aggregate(sections: list[dict], source_id: str) -> tuple[dict | None, dict, dict, list]:
    merged = {key: [] for key in COLLECTIONS}
    merged['identity_evidence'] = {}
    candidates = {key: [] for key in IDENTITY if key != 'substances'}
    for section in sections:
        info = section['information']
        for key in COLLECTIONS:
            merged[key].extend(info.get(key, []))
        for key in candidates:
            if info.get(key) is not None:
                candidates[key].append(info[key])
        for key, evidence in info.get('identity_evidence', {}).items():
            previous = merged['identity_evidence'].get(key)
            merged['identity_evidence'][key] = (previous or []) + (evidence or []) or None
    conflicts, warnings = {}, []
    for key, values in candidates.items():
        values = merge_duplicates(values)
        if len(values) > 1:
            conflicts[key] = values
            warnings.append(f'conflicting_identity:{key}')
        merged[key] = values[0] if len(values) == 1 else None
    merged = normalize(merged)
    merged['id'] = source_id
    if not merged['name']:
        warnings.append('no_unambiguous_product_name')
        return None, merged, conflicts, warnings
    # Runtime validation has already materialized nested types per section.
    product = asdict(ontology.Product(**merged))
    return product, {}, conflicts, warnings


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def process_document(client: Any, *, model: str, prompts: dict, metadata: dict,
                     sections: list[dict], template: str, warnings: list,
                     output_path: Path, overwrite: bool = False) -> bool:
    """Checkpoint each validated section and atomically publish final JSON."""
    run = digest(encoded({'version': VERSION, 'metadata': metadata, 'model': model,
                          'prompts': prompts, 'implementation': {
                              name: digest((ROOT / name).read_text(encoding='utf-8'))
                              for name in ('extract_smpc.py', 'ontology.py', 'parse_package_inserts.py')}}))
    pending = output_path.with_suffix('.json.incomplete')
    if output_path.exists() and not pending.exists() and not overwrite:
        previous = json.loads(output_path.read_text(encoding='utf-8'))
        if previous.get('run_fingerprint') != run:
            raise ValueError(f'{output_path}: configuration changed; use --overwrite')
        print(f'Skipping completed document: {output_path}')
        return False
    state = {'schema_version': VERSION, 'status': 'incomplete', 'run_fingerprint': run,
             'metadata': metadata, 'model': model, 'template': template,
             'prompt_hashes': {k: digest(v) for k, v in prompts.items()},
             'parser_warnings': warnings, 'sections': []}
    if pending.exists() and not overwrite:
        state = json.loads(pending.read_text(encoding='utf-8'))
        if state.get('run_fingerprint') != run:
            raise ValueError(f'{pending}: configuration changed; use --overwrite')
    atomic_json(pending, state)
    if warnings:
        print(f"{metadata['source_id']}: {'; '.join(warnings)}", file=sys.stderr)
    done = {s['section_id']: s for s in state['sections']}
    for source in sections:
        section = dict(source)
        section['section_id'] = (
            f"smpc:{section['document_index']}:{section['number'] or 'introduction'}@{section['start']}")
        identifier = section['section_id']
        if identifier not in done:
            body = section['text'][section['heading_end'] - section['start']:]
            has_body = bool(re.sub(
                r'</?[A-Za-z][A-Za-z0-9]*(?:\s+[^<>\n]*)?\s*/?>|[\s#*_`]', '', body))
            try:
                info = extract_section(client, model, prompts, section, metadata, template) if has_body else {}
            except Exception as exc:
                raise RuntimeError(f"{metadata['source_id']}, section {identifier}: {exc}") from exc
            section.update(information=info, status='extracted' if has_body else 'heading_only',
                           guidance_prompt=section_guidance(section, template))
            state['sections'].append(section)
            done[identifier] = section
            atomic_json(pending, state)
        print(f"{metadata['record_name']} | {identifier} | {section['title']}")
        print(json.dumps(done[identifier]['information'], ensure_ascii=False, indent=2), flush=True)
    product, partial, conflicts, normalization_warnings = aggregate(state['sections'], metadata['source_id'])
    state.update(status='complete', product=product, identity_conflicts=conflicts,
                 normalization_warnings=normalization_warnings)
    if partial:
        state['partial_product'] = partial
    atomic_json(output_path, state)
    pending.unlink()
    print(f'Saved {output_path}', flush=True)
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument('--input', type=Path, help='Raw bilingual JSONL or Arrow file.')
    source.add_argument('--data-dir', type=Path, help='Directory containing pil_spc_<split>.jsonl.')
    parser.add_argument('--dataset', default=DATASET_ID)
    parser.add_argument('--language', required=True, choices=('en', 'sk'))
    parser.add_argument('--split', default='train', choices=('train', 'test', 'validation', 'dev'))
    parser.add_argument('--model', help='Defaults to MODEL_NAME in the environment or .env.')
    parser.add_argument('--prompt-dir', type=Path, default=ROOT / 'prompts')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'output' / 'smpc')
    parser.add_argument('--limit', type=int, help='Maximum input records, including skipped records.')
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error('--limit must be positive')
    return args


def main() -> int:
    args = parse_args()
    from dotenv import load_dotenv
    from openai import OpenAI
    load_dotenv(ROOT / '.env')
    model = args.model or os.getenv('MODEL_NAME')
    token = os.getenv('AUTH_TOKEN') or os.getenv('OPENAI_API_KEY')
    base_url = os.getenv('BASE_URL') or os.getenv('OPENAI_BASE_URL')
    if not model or not token:
        raise ValueError('Set MODEL_NAME or --model, and AUTH_TOKEN or OPENAI_API_KEY.')
    prompts = {name: (args.prompt_dir / name).read_text(encoding='utf-8') for name in PROMPTS}
    if any(not text.strip() for text in prompts.values()):
        raise ValueError('Prompt files must not be empty')
    options = {'api_key': token}
    if base_url:
        options['base_url'] = base_url
    client = OpenAI(**options)
    if args.input or args.data_dir:
        path = args.input or args.data_dir / f'pil_spc_{args.split}.jsonl'
        records = records_from(path)
        input_source = str(path.resolve())
    else:
        from datasets import load_dataset
        records = load_dataset(args.dataset, split='validation' if args.split == 'dev' else args.split)
        input_source = args.dataset
    processed = skipped = failed = 0
    for index, record in enumerate(islice(records, args.limit)):
        text = record.get(args.language)
        name = str(record.get('name') or f'record-{index}')
        if not isinstance(text, str) or not text.strip():
            print(f'Skipping {name}: no raw {args.language} text', file=sys.stderr)
            skipped += 1
            continue
        parsed = parse_smpc(text, args.language)
        groups = {}
        for section in parsed['sections']:
            groups.setdefault(section['document_index'], []).append(section)
        groups = {i: spans for i, spans in groups.items() if any(s['number'] for s in spans)}
        if not groups:
            print(f'Skipping {name}: no recognizable SmPC sections', file=sys.stderr)
            skipped += 1
            continue
        source_hash = digest(text)
        record_id = str(record.get('document_id') or record.get('id') or name)
        record_key = digest(encoded([record_id, source_hash]))[:20]
        slug = re.sub(r'[^\w.-]+', '_', name, flags=re.UNICODE).strip('_.')[:80] or 'document'
        for document_index, sections in groups.items():
            source_id = f'{record_id}|{args.language}|{source_hash}|smpc:{document_index}'
            metadata = {'source_id': source_id, 'record_id': record_id, 'record_name': name,
                        'input_source': input_source, 'split': args.split,
                        'source_sha256': source_hash, 'language': args.language,
                        'document_index': document_index,
                        'start': sections[0]['start'], 'end': sections[-1]['end']}
            warnings = [w for w in parsed['warnings']
                        if not w.startswith('smpc:') or w.startswith(f'smpc:{document_index}:')]
            output_path = args.output_dir / args.language / args.split / f'{slug}-{record_key}-smpc-{document_index}.json'
            try:
                changed = process_document(client, model=model, prompts=prompts,
                                           metadata=metadata, sections=sections,
                                           template=parsed['template'], warnings=warnings,
                                           output_path=output_path, overwrite=args.overwrite)
                processed += int(changed)
                skipped += int(not changed)
            except Exception as exc:
                failed += 1
                print(f'Failed {source_id}: {exc}', file=sys.stderr)
    print(f'Completed: {processed} SmPCs saved, {skipped} skipped, {failed} failed.')
    return 1 if failed else 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print('Interrupted; completed sections remain checkpointed.', file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:
        print(f'Error: {exc}', file=sys.stderr)
        raise SystemExit(1)
