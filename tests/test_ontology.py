import inspect
import json
import types
import unittest
from dataclasses import MISSING, asdict, fields
from typing import get_args, get_origin, get_type_hints

import ontology


class OntologyTests(unittest.TestCase):
    def test_keyword_only_constructors_and_nullable_defaults(self):
        classes = (
            ontology.Evidence, ontology.Statement, ontology.Population,
            ontology.Indication, ontology.Contraindication,
            ontology.DoseRecommendation, ontology.AdverseReaction,
            ontology.Warning, ontology.Interaction, ontology.Product,
            ontology.Overdose, ontology.Pharmacodynamics,
            ontology.Pharmacokinetics, ontology.PreclinicalSafety,
        )
        for cls in classes:
            with self.subTest(cls=cls.__name__):
                hints = get_type_hints(cls)
                for parameter in inspect.signature(cls).parameters.values():
                    self.assertEqual(parameter.kind, inspect.Parameter.KEYWORD_ONLY)
                for attribute in fields(cls):
                    hint = hints[attribute.name]
                    if get_origin(hint) is types.UnionType and type(None) in get_args(hint):
                        self.assertIsNone(attribute.default)

    def test_required_statement_and_identity_fields(self):
        for cls, names in (
            (ontology.Statement, ('summary',)),
            (ontology.Evidence, ('source_id', 'exact_text')),
            (ontology.Product, ('id', 'name')),
        ):
            attributes = {attribute.name: attribute for attribute in fields(cls)}
            for name in names:
                with self.subTest(cls=cls.__name__, field=name):
                    self.assertIs(attributes[name].default, MISSING)
                    self.assertIs(attributes[name].default_factory, MISSING)

    def test_renamed_fields_and_minimal_construction(self):
        for cls in (ontology.Indication, ontology.Contraindication):
            statement = cls(evidence=[], summary='Source statement', conditions=['condition'])
            self.assertEqual(statement.conditions, ['condition'])
            self.assertIsNone(statement.populations)
            with self.assertRaises(TypeError):
                cls(evidence=[], summary='Source statement', condition=['condition'])
        self.assertIsNone(ontology.Warning(evidence=[], summary='Warning').conditions)
        self.assertFalse(hasattr(ontology, 'ContraIndication'))

    def test_product_collections_are_independent(self):
        first = ontology.Product(id='first', name='First')
        second = ontology.Product(id='second', name='Second')
        for attribute in fields(first):
            if attribute.default_factory is list:
                with self.subTest(field=attribute.name):
                    left = getattr(first, attribute.name)
                    right = getattr(second, attribute.name)
                    self.assertEqual(left, [])
                    self.assertIsNot(left, right)
        first.identity_evidence['name'] = []
        self.assertEqual(second.identity_evidence, {})

    def test_clinical_details_and_provenance_serialize(self):
        text = 'Example source statement'
        evidence = ontology.Evidence(
            source_id='source', exact_text=text, section_id='smpc:1:4.2@0',
            span_start=0, span_end=len(text), is_exact=True,
        )
        population = ontology.Population(evidence=[evidence], summary=text, name='Source group')
        dose = ontology.DoseRecommendation(
            evidence=[evidence], summary=text, populations=[population],
            adjustment='Source adjustment', administration_instructions='Source instruction',
        )
        reaction = ontology.AdverseReaction(
            evidence=[evidence], summary=text, event='Source event', frequency='not known',
            populations=[population],
        )
        product = ontology.Product(
            id='product', name='Source product', pharmaceutical_form='Source form',
            manufacturer='Manufacturer', marketing_authorisation_holder='Holder',
            identity_evidence={'name': [evidence]}, dosage=[dose], adverse_reactions=[reaction],
            overdose=[ontology.Overdose(evidence=[evidence], summary=text,
                                        management='Supportive care')],
            pharmacodynamics=[ontology.Pharmacodynamics(
                evidence=[evidence], summary=text, mechanism_of_action='Source mechanism')],
            pharmacokinetics=[ontology.Pharmacokinetics(
                evidence=[evidence], summary=text, absorption='Source absorption')],
            preclinical_safety=[ontology.PreclinicalSafety(
                evidence=[evidence], summary=text, findings=['Source finding'])],
        )
        data = json.loads(json.dumps(asdict(product)))
        self.assertEqual(data['dosage'][0]['populations'][0]['name'], 'Source group')
        self.assertEqual(data['dosage'][0]['adjustment'], 'Source adjustment')
        self.assertEqual(data['dosage'][0]['administration_instructions'], 'Source instruction')
        self.assertEqual(data['adverse_reactions'][0]['frequency'], 'not known')
        self.assertEqual(data['overdose'][0]['management'], 'Supportive care')
        self.assertEqual(data['pharmacodynamics'][0]['mechanism_of_action'], 'Source mechanism')
        self.assertEqual(data['pharmacokinetics'][0]['absorption'], 'Source absorption')
        self.assertEqual(data['preclinical_safety'][0]['findings'], ['Source finding'])
        self.assertIsNone(data['adverse_reactions'][0]['severity'])
        self.assertEqual(data['identity_evidence']['name'][0]['section_id'], 'smpc:1:4.2@0')
        self.assertNotEqual(data['manufacturer'], data['marketing_authorisation_holder'])
        self.assertEqual(text[evidence.span_start:evidence.span_end], evidence.exact_text)


if __name__ == '__main__':
    unittest.main()
