import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from parse_package_inserts import parse_insert, parse_record


class ParserTests(unittest.TestCase):
    def check_lossless(self, text, language):
        parsed = parse_insert(text, language)
        self.assertEqual(''.join(s['text'] for s in parsed['sections']), text)
        for section in parsed['sections']:
            self.assertEqual(section['text'], text[section['start']:section['end']])
            self.assertLessEqual(section['start'], section['heading_end'])
            self.assertLessEqual(section['heading_end'], section['end'])
        return parsed

    def test_smpc_inline_grouped_headings_and_references(self):
        text = ('## **ANNEX I**\n**SUMMARY OF PRODUCT CHARACTERISTICS**\n'
                '**1. NAME OF THE MEDICINAL PRODUCT** Drug\n'
                '**4. CLINICAL PARTICULARS 4.1 Therapeutic indications** Indication. '
                '**4.2 Posology and method of administration** See section 4.3. '
                '**4.3 Contraindications** Allergy. **4.8 Undesirable effects** Nausea.')
        doc = self.check_lossless(text, 'en')
        self.assertEqual([s['number'] for s in doc['sections'] if s['number']],
                         ['1', '4', '4.1', '4.2', '4.3', '4.8'])
        self.assertEqual(doc['sections'][-1]['parent_number'], '4')

    def test_comparison_signs_do_not_swallow_text(self):
        text = ('**4.2 Dávkovanie a spôsob podávania** Deti < 18 rokov. '
                '**4.3 Kontraindikácie** Dávka > 10 mg. '
                '**4.4 Osobitné upozornenia a opatrenia pri užívaní** Text.')
        doc = self.check_lossless(text, 'sk')
        self.assertEqual([s['number'] for s in doc['sections']], ['4.2', '4.3', '4.4'])

    def test_ocr_html_and_split_titles(self):
        text = ('ANNEX I<br>SUMMARY OF PRODUCT CHARACTERISTICS<br>'
                '1. NAME OF THE MEDICINAL PRODUCT<br>Drug<br>'
                '9. DATE OF FIRST AUTHORISATION/ RENEWAL OF THE AUTHORISATION<br>Date')
        doc = self.check_lossless(text, 'en')
        self.assertEqual([s['number'] for s in doc['sections'] if s['number']], ['1', '9'])

    def test_label_context_and_repeated_smpcs(self):
        text = ('**ANNEX I**\n**1. NAME OF THE MEDICINAL PRODUCT** Drug 1\n'
                '**1. NAME OF THE MEDICINAL PRODUCT** Drug 2\n'
                '**ANNEX II**\nConditions\n**ANNEX III**\n'
                '**1. NAME OF THE MEDICINAL PRODUCT** Label\n'
                '**4. PHARMACEUTICAL FORM AND CONTENTS** Tablets')
        doc = self.check_lossless(text, 'en')
        ones = [s for s in doc['sections'] if s['number']=='1']
        self.assertEqual([(s['kind'], s['document_index']) for s in ones],
                         [('smpc', 1), ('smpc', 2), ('labelling', 1)])

    def test_leaflet_toc_and_repeated_leaflets(self):
        for language, title, headings in [
            ('en', 'Package leaflet: information for the user',
             ['What Drug is and what it is used for', 'What you need to know before you take Drug',
              'How to take Drug', 'Possible side effects', 'How to store Drug',
              'Contents of the pack and other information']),
            ('sk', 'Písomná informácia pre používateľa',
             ['Čo je Liek a na čo sa používa', 'Čo potrebujete vedieť predtým, ako užijete Liek',
              'Ako užívať Liek', 'Možné vedľajšie účinky', 'Ako uchovávať Liek',
              'Obsah balenia a ďalšie informácie']),
        ]:
            toc = '\n'.join(f'{n}. {h}' for n, h in enumerate(headings, 1))
            body = '\n'.join(f'## **{n}. {h}**\nBody.' for n, h in enumerate(headings, 1))
            text = f'**{title}**\nContents\n{toc}\n{body}\n**{title}**\n{body}'
            doc = self.check_lossless(text, language)
            numbered = [s for s in doc['sections'] if s['number']]
            self.assertEqual([s['number'] for s in numbered], list('123456') * 2)
            self.assertEqual([s['document_index'] for s in numbered], [1]*6 + [2]*6)
            self.assertEqual(doc['warnings'], [])

    def test_leaflet_body_reference_is_not_heading(self):
        text = ('**1. What Drug is and what it is used for**\nBody. '
                '**3. How to use Drug**\nBody. '
                '**6. Contents of the pack and other information**\n'
                'Read section 3. How to use Drug. More information.')
        doc = self.check_lossless(text, 'en')
        self.assertEqual([s['number'] for s in doc['sections']], ['1', '3', '6'])

    def test_inline_contents_list_is_not_a_separate_leaflet(self):
        text = ('**Package leaflet: information for the user**\n'
                '**What is in this leaflet** 1. What Drug is and what it is used for '
                '2. What you need to know before you take Drug 3. How to take Drug '
                '4. Possible side effects 5. How to store Drug '
                '6. Contents of the pack and other information '
                '**1. What Drug is and what it is used for** Body. '
                '**4. Possible side effects** Effects not listed in this leaflet. '
                '**5. How to store Drug** Store. '
                '**6. Contents of the pack and other information** Contents.')
        doc = self.check_lossless(text, 'en')
        numbered = [s for s in doc['sections'] if s['number']]
        self.assertEqual([s['number'] for s in numbered], ['1', '4', '5', '6'])
        self.assertEqual({s['document_index'] for s in numbered}, {1})

    def test_infusion_heading_variants(self):
        for language, text in [
            ('en', '**3 How Drug is given to you** Body.'),
            ('sk', '**3. Ako sa Liek podáva** Body.'),
            ('sk', '**3. Ako vám bude podané Rytelo** Body.'),
        ]:
            doc = self.check_lossless(text, language)
            self.assertEqual(doc['sections'][0]['number'], '3')

    def test_unicode_offsets_with_combining_accents(self):
        text = '**4.8 Nez\u030ciaduce úc\u030cinky** Text < 18.'
        doc = self.check_lossless(text, 'sk')
        self.assertEqual(doc['sections'][0]['number'], '4.8')

    def test_veterinary_numbering_and_leaflets(self):
        for language, name, target, leaflet, other in [
            ('en', 'NAME OF THE VETERINARY MEDICINAL PRODUCT', 'Target species',
             'B. PACKAGE LEAFLET', 'OTHER INFORMATION'),
            ('sk', 'NÁZOV VETERINÁRNEHO LIEKU', 'Cieľový druh',
             'B. PÍSOMNÁ INFORMÁCIA PRE POUŽÍVATEĽOV', 'ĎALŠIE INFORMÁCIE'),
        ]:
            text = (f'**1. {name}** Drug\n**4.1 {target}** Species\n'
                    '**4.10 Overdose** None\n'
                    f'**{leaflet}**\n**1. NAME AND ADDRESS** Holder\n'
                    '**3. ACTIVE SUBSTANCE** Ingredient\n'
                    f'**15. {other}** Text\n1. Add solvent.\n')
            doc = self.check_lossless(text, language)
            self.assertEqual(doc['template'], 'veterinary')
            self.assertEqual([s['number'] for s in doc['sections'] if s['number']],
                             ['1', '4.1', '4.10', '1', '3', '15'])
            self.assertEqual(doc['sections'][-1]['kind'], 'pil')

    def test_empty_unknown_and_invalid_language(self):
        self.assertIn('empty_text', parse_insert('', 'en')['warnings'])
        self.assertIn('no_numbered_sections', self.check_lossless('No headings.', 'sk')['warnings'])
        with self.assertRaises(ValueError):
            parse_insert('text', 'de')
        record = parse_record({'name': 'Drug', 'id': 7, 'sk': None})
        self.assertEqual(record['id'], 7)
        self.assertIn('empty_text', record['sk']['warnings'])

    def test_jsonl_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, output, report = [root / name for name in ['in.jsonl', 'out.jsonl', 'report.json']]
            source.write_text(json.dumps({'name':'Drug', 'en':'**4.8 Undesirable effects** Text', 'sk':''})+'\n')
            subprocess.run([sys.executable, 'parse_package_inserts.py', '--input', str(source),
                            '--output', str(output), '--report', str(report)], check=True, capture_output=True)
            self.assertEqual(json.loads(output.read_text())['en']['sections'][0]['number'], '4.8')
            self.assertEqual(json.loads(report.read_text())['records'], 1)


if __name__ == '__main__':
    unittest.main()
