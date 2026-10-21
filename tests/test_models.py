import copy
import json
import unittest
from unittest.mock import patch

from bleo import (APIError, Automatic, ClaudeHaiku, ClaudeSonnet, GptLuna, History,
                  Llama31_8b, Qwen36, list_models, model_info, refresh_models, resolve_model)
from bleo import models
from helpers import Raw
from bleo._http import Response


def entry(name='new-model', **overrides):
    model = {'display_name': 'New model', 'capabilities': ['chat'], 'is_near_model': False,
             'options': {'name': name, 'display_maker': 'Maker', 'access': 'basic_and_premium'}}
    model.update(overrides)
    return model


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.original = copy.deepcopy(models._MODELS)
        self.addCleanup(setattr, models, '_MODELS', self.original)

    def test_defaults_and_legacy_constants_remain_compatible(self):
        self.assertEqual(resolve_model(None), ClaudeHaiku)
        self.assertEqual(resolve_model('claude-haiku'), 'claude-3-haiku')
        self.assertEqual(resolve_model('  '), ClaudeHaiku)
        self.assertEqual(History().model, ClaudeHaiku)
        self.assertEqual(resolve_model('llama'), Llama31_8b)
        self.assertNotIn(Llama31_8b, list_models())
        self.assertFalse(model_info('haiku')['advertised'])

    def test_aliases_and_future_ids(self):
        for alias, expected in [(' Haiku ', ClaudeHaiku), ('LUNA', GptLuna),
                                ('sonnet', ClaudeSonnet), ('qwen', Qwen36),
                                ('auto', Automatic), (' future-model ', 'future-model')]:
            with self.subTest(alias=alias):
                self.assertEqual(resolve_model(alias), expected)

    def test_current_catalog_and_tier_filters(self):
        all_models = list_models()
        self.assertEqual(len(all_models), len(set(all_models)))
        self.assertIn(ClaudeHaiku, list_models('free'))
        self.assertIn(GptLuna, list_models('free'))
        self.assertIn(ClaudeSonnet, all_models)
        self.assertNotIn(ClaudeSonnet, list_models('free'))
        self.assertEqual(set(all_models), set(list_models('premium')))
        with self.assertRaises(ValueError):
            list_models('invalid')

    def test_encrypted_and_summary_models_are_not_direct_chat(self):
        for name in ('near-glm-5', 'near-glm-5-1', 'brave-summary'):
            self.assertIsNotNone(model_info(name))
            self.assertNotIn(name, list_models())
        self.assertTrue(model_info('near-glm-5')['encrypted'])

    def test_metadata_is_independent_and_missing_is_none(self):
        info = model_info('luna')
        info['capabilities'].clear()
        info['name'] = 'changed'
        self.assertIn('chat', model_info('luna')['capabilities'])
        self.assertNotEqual(model_info('luna')['name'], 'changed')
        self.assertIsNone(model_info('unknown-model'))

    def fetch(self, data, status=200):
        raw = Raw(json.dumps(data).encode(), status=status)
        response = Response(raw)
        patcher = patch('bleo.models.Session')
        session = patcher.start().return_value
        self.addCleanup(patcher.stop)
        session.get.return_value = response
        return session

    def test_live_refresh_is_explicit_and_replaces_catalog(self):
        session = self.fetch([entry()])
        self.assertEqual(refresh_models(timeout=7), [ClaudeHaiku, Automatic, 'new-model'])
        session.get.assert_called_once_with('https://ai-chat.bsg.brave.com/v1/models')
        session.close.assert_called_once()
        self.assertTrue(model_info('new-model')['advertised'])
        self.assertEqual(resolve_model(None), ClaudeHaiku)

    def test_refresh_uses_wire_name_and_filters_capabilities(self):
        premium = entry('paid', options={'name': 'wire-id', 'display_maker': 'Maker', 'access': 'premium'})
        self.fetch([premium, entry('encrypted', is_near_model=True), entry('summary', capabilities=['summary'])])
        refresh_models()
        self.assertIn('wire-id', list_models())
        self.assertNotIn('wire-id', list_models('free'))
        self.assertNotIn('encrypted', list_models())
        self.assertNotIn('summary', list_models())

    def test_invalid_refresh_preserves_previous_snapshot_and_closes(self):
        cases = [{}, [], [None], [{}], [entry(), entry()],
                 [entry(capabilities='chat')], [entry(is_near_model='yes')],
                 [entry(options={'name': 'new', 'display_maker': 'Maker', 'access': 'unknown'})]]
        for data in cases:
            with self.subTest(data=data):
                session = self.fetch(data)
                with self.assertRaises(APIError):
                    refresh_models()
                self.assertEqual(models._MODELS, self.original)
                session.close.assert_called_once()

    def test_failed_refresh_preserves_catalog(self):
        session = self.fetch([], status=503)
        with self.assertRaises(APIError) as caught:
            refresh_models()
        self.assertEqual(caught.exception.status_code, 503)
        self.assertEqual(models._MODELS, self.original)
        session.close.assert_called_once()
