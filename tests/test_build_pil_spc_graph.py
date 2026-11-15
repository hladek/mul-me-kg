import argparse
import contextlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

import build_pil_spc_graph as builder


def response(text):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])


def triple(**updates):
    value = dict(subject='drug|en|example', predicate='HAS_DOSE_RECOMMENDATION',
                 object='dose|en|example|1', subject_type='Drug',
                 object_type='DoseRecommendation', source_document='model-guessed-document',
                 language='en', source_section='model-guessed-section', evidence='ALPHA')
    value.update(updates)
    return value


class SectionExtractionTests(unittest.TestCase):
    def extract(self, text, responses, language='en'):
        client = MagicMock()
        client.chat.completions.create.side_effect = [response(r) for r in responses]
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            result = builder.extract_document_triples(
                client, model='test', system_prompt='extract', text=text,
                language=language, name='example', source_document='document-1',
            )
        return result, client

    def test_real_parser_sections_and_authoritative_provenance(self):
        text = ('**4.2 Posology and method of administration** ALPHA\n'
                '**4.3 Contraindications** BETA')
        fact = triple()
        property_row = triple(subject=fact['object'], predicate='description',
                              object='dose|literal text', subject_type='DoseRecommendation',
                              object_type='Literal')
        rows = '\n'.join(json.dumps(r) for r in [fact, property_row])
        (triples, count), client = self.extract(text, [rows, rows])
        self.assertEqual(count, 2)
        calls = client.chat.completions.create.call_args_list
        first, second = [call.kwargs['messages'][1]['content'] for call in calls]
        first_source = first.split('----- BEGIN SOURCE SECTION -----\n')[1]
        second_source = second.split('----- BEGIN SOURCE SECTION -----\n')[1]
        self.assertIn('ALPHA', first_source)
        self.assertNotIn('BETA', first_source)
        self.assertIn('BETA', second_source)
        self.assertNotIn('ALPHA', second_source)
        self.assertEqual({t['source_document'] for t in triples}, {'document-1'})
        self.assertTrue(triples[0]['source_section'].startswith('smpc:1:4.2@'))
        self.assertTrue(triples[2]['source_section'].startswith('smpc:1:4.3@'))
        # A property stays connected to its fact, and sections cannot reuse it.
        self.assertEqual(triples[0]['object'], triples[1]['subject'])
        self.assertNotEqual(triples[0]['object'], triples[2]['object'])
        self.assertEqual(triples[1]['object'], 'dose|literal text')
        self.assertNotEqual(builder.assertion_id(triples[0]), builder.assertion_id(triples[2]))

    def test_slovak_sections(self):
        text = ('**4.2 Dávkovanie a spôsob podávania** ALFA\n'
                '**4.3 Kontraindikácie** BETA')
        row = json.dumps(triple(language='sk'))
        (triples, count), _ = self.extract(text, [row, '[]'], language='sk')
        self.assertEqual(count, 2)
        self.assertEqual(len(triples), 1)
        self.assertEqual(triples[0]['language'], 'sk')

    def test_no_facts_and_heading_only_spans(self):
        text = ('**ANNEX I**\n**SUMMARY OF PRODUCT CHARACTERISTICS**\n'
                '**4. CLINICAL PARTICULARS**\n**4.3 Contraindications** None.')
        (triples, count), client = self.extract(text, ['[]'])
        self.assertEqual((triples, count), ([], 1))
        self.assertEqual(client.chat.completions.create.call_count, 1)
        self.assertIn('Return []', client.chat.completions.create.call_args.kwargs['messages'][1]['content'])

    def test_unrecognized_text_is_still_extracted(self):
        (triples, count), _ = self.extract('Unstructured source text.', ['[]'])
        self.assertEqual((triples, count), ([], 1))

    def test_invalid_response_is_reported_with_section_context(self):
        with self.assertRaisesRegex(RuntimeError, r'section smpc:1:4.3@0'):
            self.extract('**4.3 Contraindications** Text.', ['not JSONL'])
        with self.assertRaisesRegex(ValueError, 'expected'):
            builder.parse_triples(json.dumps(triple(language='sk')), language='en', record_name='test')


class PipelineTests(unittest.TestCase):
    def run_pipeline(self, root, client, graph, records):
        prompt = root / 'prompt.txt'
        prompt.write_text('extract', encoding='utf-8')
        args = argparse.Namespace(language='en', split='train', data_dir=None,
                                  dataset='test', prompt=prompt, output_dir=root/'output',
                                  cog_home=root/'cog', graph_name=None, model='test',
                                  limit=None, overwrite=False)
        with (patch.object(builder, 'parse_args', return_value=args),
              patch.object(builder, 'load_dotenv'),
              patch.object(builder.os, 'getenv', return_value='test-token'),
              patch.object(builder, 'OpenAI', return_value=client),
              patch.object(builder, 'Graph', return_value=graph),
              patch.object(builder, 'get_records', return_value=records),
              contextlib.redirect_stdout(io.StringIO()),
              contextlib.redirect_stderr(io.StringIO())):
            return builder.main()

    def test_document_outputs_graph_import_and_resume_with_duplicate_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            records = [{'name':'same', 'en':'**4.3 Contraindications** ALPHA'},
                       {'name':'same', 'en':'**4.3 Contraindications** BETA'}]
            client, graph = MagicMock(), MagicMock()
            client.chat.completions.create.side_effect = [response(json.dumps(triple())), response('[]')]
            self.assertEqual(self.run_pipeline(root, client, graph, records), 0)
            files = sorted((root/'output'/'en'/'train').glob('*.jsonl'))
            self.assertEqual(len(files), 2)
            rows = [json.loads(line) for p in files for line in p.read_text().splitlines()]
            self.assertEqual(len(rows), 1)
            graph.put.assert_any_call('drug|en|example', 'HAS_DOSE_RECOMMENDATION', rows[0]['object'])
            graph.put.assert_any_call(builder.assertion_id(rows[0]), 'source_section', rows[0]['source_section'])
            client.reset_mock()
            self.run_pipeline(root, client, graph, records)
            client.chat.completions.create.assert_not_called()

    def test_failed_section_preserves_partial_knowledge_and_retry_deduplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            records = [{'name':'example', 'en': '**4.2 Posology and method of administration** ALPHA\n'
                                               '**4.3 Contraindications** BETA'}]
            client, graph = MagicMock(), MagicMock()
            client.chat.completions.create.side_effect = [response(json.dumps(triple())), response('invalid')]
            with self.assertRaises(RuntimeError):
                self.run_pipeline(root, client, graph, records)
            files = list((root/'output').rglob('*.jsonl'))
            self.assertEqual(len(files), 1)
            first_rows = [json.loads(line) for line in files[0].read_text().splitlines()]
            self.assertEqual(len(first_rows), 1)
            self.assertTrue(files[0].with_suffix('.jsonl.incomplete').exists())
            graph.put.assert_not_called()
            # Repeating the first section does not duplicate saved assertions.
            client.chat.completions.create.side_effect = [response(json.dumps(triple())), response('[]')]
            self.run_pipeline(root, client, graph, records)
            self.assertEqual([json.loads(line) for line in files[0].read_text().splitlines()], first_rows)
            self.assertFalse(files[0].with_suffix('.jsonl.incomplete').exists())

    def test_graph_failure_does_not_mark_document_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            client, graph = MagicMock(), MagicMock()
            client.chat.completions.create.return_value = response(json.dumps(triple()))
            graph.put.side_effect = RuntimeError('storage failure')
            with self.assertRaisesRegex(RuntimeError, 'storage failure'):
                self.run_pipeline(root, client, graph, [{'name':'example','en':'Unstructured text'}])
            files = list((root/'output').rglob('*.jsonl'))
            self.assertEqual(len(files), 1)
            self.assertTrue(files[0].with_suffix('.jsonl.incomplete').exists())
            self.assertEqual(len(files[0].read_text().splitlines()), 1)

    def test_each_section_is_written_before_next_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            records = [{'name':'example', 'en':'**4.2 Posology and method of administration** ALPHA\n'
                                             '**4.3 Contraindications** BETA'}]
            client, graph = MagicMock(), MagicMock()
            calls = 0

            def extract(**kwargs):
                nonlocal calls
                calls += 1
                if calls == 2:
                    files = list((root/'output').rglob('*.jsonl'))
                    self.assertEqual(len(files), 1)
                    saved = json.loads(files[0].read_text())
                    self.assertTrue(saved['source_section'].startswith('smpc:1:4.2@'))
                    self.assertIn('|section-', saved['object'])
                return response(json.dumps(triple(evidence='ALPHA' if calls == 1 else 'BETA')))

            client.chat.completions.create.side_effect = extract
            self.run_pipeline(root, client, graph, records)
            saved = [json.loads(line) for line in next((root/'output').rglob('*.jsonl')).read_text().splitlines()]
            self.assertEqual([row['evidence'] for row in saved], ['ALPHA', 'BETA'])

    def test_dev_alias_for_remote_dataset(self):
        with patch.object(builder, 'load_dataset', return_value=[]) as load:
            builder.get_records(argparse.Namespace(data_dir=None, dataset='test', split='dev'))
        load.assert_called_once_with('test', split='validation')


if __name__ == '__main__':
    unittest.main()
