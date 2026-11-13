#!/usr/bin/env python3
"""Lossless, rule-based sectioning of English and Slovak EMA product information."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from functools import lru_cache
from pathlib import Path
import re
import unicodedata

DATASET_ID = "multilingual-medical-kg/pil-spc"

# Standard human-medicine QRD headings. IDs are shared across languages;
# original headings and all source characters are retained in the output.
SMPC = {
    "1": ("name of the medicinal product", "názov lieku"),
    "2": ("qualitative and quantitative composition", "kvalitatívne a kvantitatívne zloženie"),
    "3": ("pharmaceutical form", "lieková forma"),
    "4": ("clinical particulars", "klinické údaje"),
    "4.1": ("therapeutic indications", "terapeutické indikácie"),
    "4.2": ("posology and method of administration", "dávkovanie a spôsob podávania"),
    "4.3": ("contraindications", "kontraindikácie"),
    "4.4": ("special warnings and precautions for use", "osobitné upozornenia a opatrenia pri (?:používaní|užívaní)"),
    "4.5": ("interaction with other medicinal products and other forms of interaction", "liekové a iné interakcie"),
    "4.6": ("fertility, pregnancy and lactation|pregnancy and lactation", "fertilita, gravidita a laktácia|gravidita a laktácia"),
    "4.7": ("effects on ability to drive and use machines", "ovplyvnenie schopnosti viesť vozidlá a obsluhovať stroje"),
    "4.8": ("undesirable effects", "nežiaduce účinky"),
    "4.9": ("overdose", "predávkovanie"),
    "5": ("pharmacological properties", "farmakologické vlastnosti"),
    "5.1": ("pharmacodynamic properties", "farmakodynamické vlastnosti"),
    "5.2": ("pharmacokinetic properties", "farmakokinetické vlastnosti"),
    "5.3": ("preclinical safety data", "predklinické údaje o bezpečnosti"),
    "6": ("pharmaceutical particulars", "farmaceutické informácie"),
    "6.1": ("list of excipients", "zoznam pomocných látok"),
    "6.2": ("incompatibilities", "inkompatibility"),
    "6.3": ("shelf life", "čas použiteľnosti"),
    "6.4": ("special precautions for storage", "špeciálne upozornenia na uchovávanie"),
    "6.5": ("nature and contents of container", "druh obalu a obsah balenia"),
    "6.6": ("special precautions for disposal and other handling|special precautions for disposal", "špeciálne opatrenia na likvidáciu a iné zaobchádzanie s liekom|špeciálne opatrenia na likvidáciu"),
    "7": ("marketing authorisation holder", "držiteľ rozhodnutia o registrácii"),
    "8": (r"marketing authorisation number(?:\(s\)|s)?", r"registračné čísl(?:o(?:\s*\(čísla\))?|a)"),
    "9": ("date of first authorisation/renewal of the authorisation", "dátum prvej registrácie/predĺženia registrácie"),
    "10": ("date of revision of the text", "dátum revízie textu"),
    "11": ("dosimetry", "dozimetria"),
    "12": ("instructions for preparation of radiopharmaceuticals", "pokyny na prípravu rádiofarmák"),
}
LABEL = {
    "1": SMPC["1"],
    "2": (r"statement of active substance(?:\(s\)|s)?|method of administration|name of the marketing authorisation holder", r"liečivo(?:\s*\(liečivá\))?|liečivá|spôsob podávania|názov držiteľa rozhodnutia o registrácii"),
    "3": ("list of excipients|expiry date", "zoznam pomocných látok|dátum exspirácie"),
    "4": ("pharmaceutical form and contents|batch number", "lieková forma a obsah|číslo výrobnej šarže"),
    "5": (r"method and route(?:\(s\))? of administration|contents by weight, by volume or by unit|other", r"spôsob a cesta(?:\s*\(cesty\))? podávania|spôsob a cesta podania|obsah v hmotnostných, objemových alebo (?:v )?kusových jednotkách|iné"),
    "6": ("special warning that the medicinal product must be stored out of the sight and reach of children|other", "špeciálne upozornenie, že liek sa musí uchovávať mimo dohľadu a dosahu detí|iné"),
    "7": (r"other special warning(?:\(s\))?, if necessary", r"iné špeciálne upozornenie(?:\s*\(upozornenia\))?, ak je to potrebné"),
    "8": ("expiry date", "dátum exspirácie"),
    "9": ("special storage conditions", "špeciálne podmienky na uchovávanie"),
    "10": ("special precautions for disposal of unused medicinal products or waste materials derived from such medicinal products, if appropriate", "špeciálne upozornenia na likvidáciu nepoužitých liekov alebo odpadov z nich vzniknutých, ak je to vhodné"),
    "11": ("name and address of the marketing authorisation holder", "názov a adresa držiteľa rozhodnutia o registrácii"),
    "12": SMPC["8"],
    "13": ("batch number", "číslo výrobnej šarže"),
    "14": ("general classification for supply", "zatriedenie lieku podľa spôsobu výdaja"),
    "15": ("instructions on use", "pokyny na použitie"),
    "16": ("information in braille", "informácie v braillovom písme"),
    "17": ("unique identifier [–-] 2d barcode", "špecifický identifikátor [–-] dvojrozmerný čiarový kód"),
    "18": ("unique identifier [–-] human readable data", "špecifický identifikátor [–-] údaje čitateľné ľudským okom"),
}
PIL = {
    "1": (r"what .{1,200}? is and what it is used for", r"čo (?:je|sú) .{1,200}? a na čo sa (?:používa|užíva)(?:jú)?"),
    "2": (r"what (?:do )?you need to know before|before you (?:take|use|are given)", r"čo (?:potrebujete?|musíte) vedieť (?:predtým|skôr)|skôr ako (?:užijete|použijete)"),
    "3": (r"how (?:to|you will be given|you are given|.{1,180}? (?:is|will be) given)", r"ako (?:užívať|používať|použiť|užíva|sa .{0,180}?podáva|podávať|vám bude .{0,180}?podan(?:ý|é|á))"),
    "4": ("possible side effects", "možné vedľajšie účinky"),
    "5": ("how to store", "ako uchovávať"),
    "6": ("contents of the pack and other information|further information", "obsah balenia a ďalšie informácie|ďalšie informácie"),
}


@lru_cache(maxsize=4096)
def fold(text: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', text.lower()) if not unicodedata.combining(c))


def searchable(text: str) -> tuple[str, list[int]]:
    """Normalize formatting for matching while mapping back to original offsets."""
    chars, offsets = [], []
    for match in re.finditer(r'</?[A-Za-z][A-Za-z0-9]*(?:\s+[^<>\n]*)?\s*/?>|[*_#`]+|[^<*_#`]+|[<]', text):
        token = match.group()
        if token.startswith('<') and token.endswith('>'):
            token = ' '  # Includes OCR <br> and HTML layout tags.
        elif token[0] in '*_#`':
            continue
        translation = {ord(char): ' ' if char.isspace() else fold(char)
                       for char in set(token)}
        if all(len(value) == 1 for value in translation.values()):
            chars.append(token.translate(translation))
            offsets.extend(range(match.start(), match.start() + len(token)))
        else:
            # Decomposed accents and uncommon case folds can change length.
            for i, char in enumerate(token):
                normalized = translation[ord(char)]
                chars.append(normalized)
                offsets.extend([match.start() + i] * len(normalized))
    return ''.join(chars), offsets


def pattern(title: str) -> str:
    return re.sub(r' +', r'\\s+', fold(title)).replace('/', r'\s*/\s*')


# Scan numbers once, then match only the titles valid for that number.
# This avoids scanning a large insert separately for every template heading.
NUMBER = re.compile(r'(?<![\w.])(?P<number>\d{1,2}(?:\.\d{1,2})?)(?:\.\s*|\s+)(?:-\s*)?')
RULES = {}
for language, column in [('en', 0), ('sk', 1)]:
    rules = {}
    for kind, table in [('smpc', SMPC), ('labelling', LABEL), ('pil', PIL)]:
        for number, titles in table.items():
            rules.setdefault(number, []).append(
                (kind, re.compile('(?:' + pattern(titles[column]) + r')(?!\w)')))
    RULES[language] = rules

MARKERS = {
    'en': r'(?<!\w)(?:annex\s+(?P<annex>iv|iii|ii|i)\b|(?P<smpc>summary\s+of\s+product\s+characteristics)|(?P<label>a\.\s*labelling)|(?P<pil>b\.\s*package\s+leaflet|package\s+leaflet\s*:\s*information\s+for\s+the\s+(?:user|patient)))',
    'sk': r'(?<!\w)(?:priloha\s+(?P<annex>iv|iii|ii|i)\b|(?P<smpc>suhrn\s+charakteristickych\s+vlastnosti\s+lieku)|(?P<label>a\.\s*oznacenie\s+obalu)|(?P<pil>b\.\s*pisomna\s+informacia\s+pre\s+pouzivatel(?:a|ov)|pisomna\s+informacia\s+pre\s+pouzivatel(?:a|ov))(?!\s+bola))',
}


def heading_start(text: str, start: int) -> int:
    # Attach leading Markdown markers, but never consume the preceding newline.
    while start and text[start - 1] in ' *\t_#`':
        start -= 1
    return start


def is_layout_start(text: str, start: int) -> bool:
    prefix = text[max(0, start - 250):start]
    return bool(re.search(r'(?:^|\n|<br\s*/?>)[ #*_`\t-]*$', prefix, re.I) or re.search(r'\*\*[ \t]*$', prefix))


def variable_title_end(text: str, start: int, minimum: int) -> int:
    """PIL titles contain product names; stop at a layout boundary."""
    boundary = re.search(r'\*\*|\n|<br\s*/?>', text[minimum:minimum + 250], re.I)
    return minimum + boundary.start() if boundary else minimum


def parse_insert(text: str, language: str) -> dict:
    """Return contiguous source spans, numbered sections, and review warnings.

    Spans form an exact partition: ''.join(s['text'] for s in sections) == text.
    document_index counts repeated SmPCs/leaflets/labels, independently per kind.
    Numbered parent sections contain only their own text, avoiding duplication.
    """
    if language not in RULES:
        raise ValueError('language must be en or sk')
    if not isinstance(text, str):
        raise TypeError('insert text must be a string')
    clean, offsets = searchable(text)
    veterinary = bool(re.search(r'(?<!\w)1[.\s]+(?:name\s+of\s+the\s+veterinary\s+medicinal\s+product|nazov\s+veterinarneho\s+lieku)', clean))
    events = []
    for match in re.finditer(MARKERS[language], clean):
        if not is_layout_start(text, offsets[match.start()]):
            continue
        group = match.lastgroup
        annex = match.group('annex')
        kind = {'i': 'smpc', 'ii': 'annex_ii', 'iii': 'labelling', 'iv': 'annex_iv'}.get(annex) if group == 'annex' else {'smpc': 'smpc', 'label': 'labelling', 'pil': 'pil'}[group]
        events.append(dict(start=heading_start(text, offsets[match.start()]), heading_end=offsets[match.end()-1]+1, kind=kind, number=None, marker=True))
    for candidate in NUMBER.finditer(clean):
        number = candidate['number']
        if veterinary and candidate.end() < len(offsets) and int(number.split('.')[0]) <= 20:
            start = offsets[candidate.start()]
            title_start = offsets[candidate.end()]
            end = variable_title_end(text, start, title_start)
            title = text[title_start:end].strip(' #*_`\t\n')
            # Veterinary QRD main headings are capitals, while numbered
            # subsections use sentence case. Ordinary numbered instructions
            # are retained in their containing section.
            if (title and is_layout_start(text, start)
                    and ((len(title.split()[0]) > 1 and title.split()[0].isupper()) or ('.' in number and title[0].isalpha()))):
                events.append(dict(start=heading_start(text, start), heading_end=end,
                                   kind='veterinary', number=number, marker=False))
        for kind, regex in RULES[language].get(number, []):
            match = regex.match(clean, candidate.end())
            if not match:
                continue
            start, end = offsets[candidate.start()], offsets[match.end()-1]+1
            if kind == 'pil' and not is_layout_start(text, start):
                continue
            if kind == 'pil' and number in {'2', '3', '5'}:
                end = variable_title_end(text, start, end)
            events.append(dict(start=heading_start(text, start), heading_end=end, kind=kind, number=number, marker=False))
    events.sort(key=lambda e: (e['start'], not e['marker'], -e['heading_end']))

    # A leaflet contents list precedes a second occurrence of section 1. Keep
    # the list in the introduction rather than emitting six empty sections.
    pil_ones = [e for e in events if e['kind'] == 'pil' and e['number'] == '1']
    toc_ranges = []
    for first, second in zip(pil_ones, pil_ones[1:]):
        if any(e['marker'] and e['kind'] == 'pil' and first['start'] < e['start'] < second['start'] for e in events):
            continue
        fragment = text[first['heading_end']:second['start']]
        inline_list = len(re.findall(r'(?<!\w)[2-6]\.\s+', fragment)) >= 4
        if second['start'] - first['start'] < 2000 and inline_list:
            toc_ranges.append((first['start'], second['start']))
            continue
        between = [e for e in events if first['start'] <= e['start'] < second['start'] and e['kind'] == 'pil' and e['number']]
        if second['start'] - first['start'] < 3500 and len(between) >= 4:
            if all(b['start'] - a['start'] < 650 for a, b in zip(between, between[1:])):
                toc_ranges.append((first['start'], second['start']))
    # Explicit contents markers also cover inline lists and OCR lists missing 1.
    toc_pattern = (r"what\s+is\s+in\s+this\s+leaflet|in\s+this\s+leaflet"
                   if language == 'en' else r"v\s+tejto\s+pisomnej\s+informacii\s+sa\s+dozviete")
    for match in re.finditer(toc_pattern, clean):
        start = offsets[match.start()]
        if not is_layout_start(text, start):
            continue
        ones = [e for e in pil_ones if start < e['start'] < start + 5000]
        if not ones:
            continue
        # The contents entry is followed by another 1; if it is missing,
        # the first 1 is already the body heading.
        first = ones[0]
        stop = first['start']
        if len(ones) > 1 and ones[1]['start'] - first['start'] < 2000:
            fragment = fold(text[first['heading_end']:ones[1]['start']])
            if ('6.' in fragment or '5.' in fragment) and len(fragment) < 2000:
                stop = ones[1]['start']
        toc_ranges.append((start, stop))
    events = [e for e in events if not any(a <= e['start'] < b for a, b in toc_ranges)]

    selected = []
    context = 'unknown'
    for event in events:
        if event['kind'] == 'veterinary':
            if context in {'annex_ii', 'annex_iv'}:
                continue
            event['kind'] = 'smpc' if context == 'unknown' else context
        if event['marker']:
            context = event['kind']
        elif event['kind'] == 'labelling' and context != 'labelling':
            continue
        elif event['kind'] == 'smpc' and context in {'labelling', 'pil', 'annex_ii', 'annex_iv'}:
            continue
        elif event['kind'] == 'pil':
            context = 'pil'
        elif context == 'unknown':
            context = event['kind']
        if selected and selected[-1]['start'] == event['start']:
            continue
        selected.append(event)
    sections = []
    if not selected or selected[0]['start']:
        sections.append(dict(kind='unknown', number=None, start=0, heading_end=0, marker=True))
    sections.extend(selected)
    indices = Counter()
    previous_kind = None
    active_index = 0
    numbered_in_document = False
    for i, section in enumerate(sections):
        kind = section['kind']
        new_kind = kind != previous_kind
        new_title = (kind == 'pil' and section['number'] is None
                     and numbered_in_document)
        if new_kind or new_title or (section['number'] == '1' and numbered_in_document):
            indices[kind] += 1
            numbered_in_document = False
        active_index = indices[kind]
        numbered_in_document = numbered_in_document or section['number'] is not None
        section['document_index'] = active_index
        previous_kind = kind
        end = sections[i + 1]['start'] if i + 1 < len(sections) else len(text)
        section['end'] = end
        section['heading_end'] = min(section['heading_end'], end)
        section['title'] = text[section['start']:section['heading_end']].strip(' #*_`\t\n')
        section['text'] = text[section['start']:end]
        section['parent_number'] = section['number'].split('.')[0] if section['number'] and '.' in section['number'] else None
        del section['marker']
    warnings = []
    if not text.strip():
        warnings.append('empty_text')
    if not any(s['number'] for s in sections):
        warnings.append('no_numbered_sections')
    groups = {}
    for s in sections:
        numbers = groups.setdefault((s['kind'], s['document_index']), [])
        if s['number']:
            numbers.append(s['number'])
    for (kind, index), numbers in groups.items():
        expected = (set(str(n) for n in range(1, max((int(n) for n in numbers if '.' not in n), default=0) + 1))
                    if veterinary else PIL if kind == 'pil' else SMPC if kind == 'smpc' else {})
        required = set(expected) - ({'11', '12'} if kind == 'smpc' else set())
        missing = sorted(required - set(numbers), key=lambda n: tuple(map(int, n.split('.'))))
        if missing:
            warnings.append(f'{kind}:{index}:missing_sections:{",".join(missing)}')
        duplicates = sorted(n for n, count in Counter(numbers).items() if count > 1)
        if duplicates:
            warnings.append(f'{kind}:{index}:repeated_sections:{",".join(duplicates)}')
    return {'language': language, 'template': 'veterinary' if veterinary else 'human',
            'sections': sections, 'warnings': warnings}


def parse_record(record: dict) -> dict:
    """Keep record metadata and replace language strings with parsed documents."""
    result = {k: v for k, v in record.items() if k not in ('sk', 'en')}
    for language in ('sk', 'en'):
        value = record.get(language)
        if value is not None and not isinstance(value, str):
            raise TypeError(f'{record.get("name", "record")}: {language} must be a string or null')
        result[language] = parse_insert(value or '', language)
    return result


def records_from(path: Path):
    if path.suffix == '.arrow':
        from datasets import Dataset
        yield from Dataset.from_file(str(path))
    else:
        with path.open(encoding='utf-8') as stream:
            for line_number, line in enumerate(stream, 1):
                if line.strip():
                    try:
                        record = json.loads(line)
                        if not isinstance(record, dict):
                            raise ValueError('expected a JSON object')
                        yield record
                    except ValueError as exc:
                        raise ValueError(f'{path}:{line_number}: {exc}') from exc


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, help='Local bilingual JSONL or Hugging Face Arrow file.')
    parser.add_argument('--dataset', default=DATASET_ID)
    parser.add_argument('--split', default='train', choices=('train', 'test', 'validation'))
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--report', type=Path, help='Optional JSON coverage report.')
    parser.add_argument('--limit', type=int)
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error('--limit must be positive')
    if args.input and args.input.resolve() == args.output.resolve():
        parser.error('--output must differ from --input')
    if args.report and args.report.resolve() in {args.output.resolve(), args.input.resolve() if args.input else None}:
        parser.error('--report must differ from input and output')
    if args.input:
        records = records_from(args.input)
    else:
        from datasets import load_dataset
        records = load_dataset(args.dataset, split=args.split)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    counts, warnings, documents = Counter(), Counter(), Counter()
    total = 0
    from itertools import islice
    with args.output.open('w', encoding='utf-8') as stream:
        for record in islice(records, args.limit):
            parsed = parse_record(record)
            for language in ('sk', 'en'):
                doc = parsed[language]
                for s in doc['sections']:
                    counts[f'{language}:{s["kind"]}'] += 1
                for kind in {s['kind'] for s in doc['sections'] if s['number']}:
                    documents[f'{language}:{kind}'] += 1
                for warning in doc['warnings']:
                    warnings[f'{language}:{warning}'] += 1
            stream.write(json.dumps(parsed, ensure_ascii=False) + '\n')
            total += 1
    report = {'records': total, 'records_with_numbered_sections': dict(documents), 'section_counts': dict(counts), 'warnings': dict(warnings)}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
