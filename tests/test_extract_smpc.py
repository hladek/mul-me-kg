import unittest

import ontology
from extract_smpc import aggregate, response_schema, validate_extraction, validate_value


class EvidenceValidationTests(unittest.TestCase):
    def setUp(self):
        self.section = {
            'text': 'Heading\nExact source excerpt. Another sentence.',
            'start': 100,
            'title': 'Heading',
            'section_id': 'smpc:1:4.4@100',
        }
        self.metadata = {
            'source_id': 'source', 'record_name': 'Document', 'language': 'en',
        }

    def validate_evidence(self, value):
        return validate_value(value, ontology.Evidence,
                              section=self.section, metadata=self.metadata)

    def test_exact_excerpt_has_document_offsets(self):
        quote = 'Exact source excerpt.'
        evidence = self.validate_evidence({'exact_text': quote})
        self.assertTrue(evidence.is_exact)
        self.assertEqual(evidence.span_start, 108)
        self.assertEqual(evidence.span_end, 108 + len(quote))
        self.assertEqual(evidence.source_id, 'source')
        self.assertEqual(evidence.section_id, self.section['section_id'])

    def test_unmatched_excerpt_is_preserved_without_offsets(self):
        quote = '  Nonverbatim excerpt.  '
        evidence = self.validate_evidence({'exact_text': quote})
        self.assertFalse(evidence.is_exact)
        self.assertEqual(evidence.exact_text, quote)
        self.assertIsNone(evidence.span_start)
        self.assertIsNone(evidence.span_end)

    def test_mixed_evidence_continues_extraction(self):
        result = validate_extraction({'warnings': [{
            'summary': 'Warning',
            'evidence': [
                {'exact_text': 'Exact source excerpt.'},
                {'exact_text': 'Nonverbatim excerpt.'},
            ],
        }, {
            'summary': 'Another warning',
            'evidence': [{'exact_text': 'Another sentence.'}],
        }]}, self.section, self.metadata)
        evidence = result['warnings'][0]['evidence']
        self.assertEqual([item['is_exact'] for item in evidence], [True, False])
        self.assertIsNone(evidence[1]['span_start'])
        self.assertIsNone(evidence[1]['span_end'])
        self.assertEqual(len(result['warnings']), 2)

    def test_malformed_evidence_is_still_rejected(self):
        for value in ({'exact_text': 42},
                      {'exact_text': 'Excerpt', 'is_exact': False}, []):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.validate_evidence(value)

    def test_response_schema_only_requests_exact_text(self):
        schema = response_schema(ontology.Evidence)
        self.assertEqual(schema['anyOf'][0], {'type': 'null'})
        excerpt = schema['anyOf'][1]
        self.assertEqual(set(excerpt['properties']), {'exact_text'})
        self.assertEqual(excerpt['required'], [])
        statement = response_schema(ontology.Warning)
        self.assertNotIn('evidence', statement['required'])
        self.assertIn({'type': 'null'}, statement['properties']['evidence']['anyOf'])

    def test_unavailable_excerpts_become_none(self):
        for value in (None, {}, {'exact_text': None}, {'exact_text': ''},
                      {'exact_text': '  \n '}):
            with self.subTest(value=value):
                self.assertIsNone(self.validate_evidence(value))

    def test_knowledge_without_evidence_is_retained(self):
        for fields in ({}, {'evidence': None}, {'evidence': []},
                       {'evidence': [None, {}, {'exact_text': None},
                                     {'exact_text': '  '}]}):
            with self.subTest(fields=fields):
                result = validate_extraction({
                    'name': 'Product', 'identity_evidence': {'name': None},
                    'warnings': [dict(summary='Warning', populations=[
                        dict(name='Adults', summary='Group', **fields),
                        dict(summary='Unnamed group', **fields),
                    ], **fields)],
                }, self.section, self.metadata)
                warning = result['warnings'][0]
                self.assertIsNone(warning['evidence'])
                self.assertEqual(warning['populations'][0]['name'], 'Adults')
                self.assertIsNone(warning['populations'][0]['evidence'])
                self.assertEqual(len(warning['populations']), 1)
                self.assertIsNone(result['identity_evidence']['name'])
        result = validate_extraction({'name': 'Product'}, self.section, self.metadata)
        self.assertEqual(result['name'], 'Product')

    def test_mixed_lists_discard_only_unavailable_excerpts(self):
        result = validate_extraction({'name': 'Product',
            'identity_evidence': {'name': [None, {}, {'exact_text': ''},
                                         {'exact_text': 'Nonverbatim'}]},
            'warnings': [{'summary': 'Warning', 'evidence': [
                None, {}, {'exact_text': None}, {'exact_text': '  '},
                {'exact_text': 'Exact source excerpt.'},
                {'exact_text': 'Nonverbatim'},
            ]}]}, self.section, self.metadata)
        self.assertEqual([v['is_exact'] for v in result['warnings'][0]['evidence']],
                         [True, False])
        self.assertEqual(len(result['identity_evidence']['name']), 1)

    def test_aggregation_preserves_evidence_in_both_merge_orders(self):
        for reverse in (False, True):
            for have_excerpt in (False, True):
                with self.subTest(reverse=reverse, have_excerpt=have_excerpt):
                    quote = [{'exact_text': 'Exact source excerpt.'}]
                    infos = [validate_extraction({
                        'name': 'Product', 'identity_evidence': {'name': evidence},
                        'warnings': [{'summary': 'Warning', 'evidence': evidence,
                                      'populations': [{'name': 'Adults',
                                                       'summary': 'Group',
                                                       'evidence': evidence}]}],
                    }, self.section, self.metadata)
                        for evidence in (None, quote if have_excerpt else None)]
                    if reverse:
                        infos.reverse()
                    product, partial, conflicts, warnings = aggregate(
                        [{'information': info} for info in infos], 'source')
                    self.assertEqual(len(product['warnings']), 1)
                    evidence = product['warnings'][0]['evidence']
                    nested = product['warnings'][0]['populations'][0]['evidence']
                    self.assertEqual(evidence, nested)
                    self.assertEqual(evidence, product['identity_evidence']['name'])
                    self.assertEqual(evidence is not None, have_excerpt)

    def test_population_without_name_becomes_none(self):
        population = {'summary': 'Patient group',
                      'evidence': [{'exact_text': 'Exact source excerpt.'}]}
        self.assertIsNone(validate_value(population, ontology.Population,
                                        section=self.section, metadata=self.metadata))

    def test_unnamed_populations_do_not_fail_extraction(self):
        unnamed = {'summary': 'Patient group',
                   'evidence': [{'exact_text': 'Exact source excerpt.'}]}
        named = dict(unnamed, name='Adults')
        for populations, expected in (([unnamed], None),
                                      ([unnamed, named], ['Adults']),
                                      ([], [])):
            with self.subTest(populations=populations):
                result = validate_extraction({'warnings': [{
                    'summary': 'Warning',
                    'evidence': [{'exact_text': 'Another sentence.'}],
                    'populations': populations,
                }]}, self.section, self.metadata)
                warning = result['warnings'][0]
                self.assertEqual(warning['summary'], 'Warning')
                actual = warning['populations']
                self.assertEqual(None if actual is None else
                                 [p['name'] for p in actual], expected)
                if actual:
                    self.assertTrue(actual[0]['evidence'][0]['is_exact'])

    def test_other_population_errors_are_still_rejected(self):
        valid = {'summary': 'Patient group',
                 'evidence': [{'exact_text': 'Exact source excerpt.'}]}
        for population in (dict(valid, name=''), dict(valid, name='  '),
                           dict(valid, name=None),
                           {'evidence': valid['evidence']},
                           dict(valid, unexpected=True)):
            with self.subTest(population=population), self.assertRaises(ValueError):
                validate_value(population, ontology.Population,
                               section=self.section, metadata=self.metadata)


if __name__ == '__main__':
    unittest.main()
