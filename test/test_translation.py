from unittest import TestCase
from test.proxytestcase import ProxyTestCase

from digit_analysis import TranslationPattern, TranslationError
from ucmexport import TranslationPattern as CSVTranslationPattern

import logging


class TestTpProxy(ProxyTestCase):
    def setUp(self) -> None:
        super(TestTpProxy, self).setUp()
        logging.getLogger('digit_analysis.base').setLevel(logging.DEBUG)

    def test_0_list(self):
        tps = self.proxy.translation_pattern.list
        self.assertIsInstance(tps, list, f'{tps.__class__}')

    def test_1_not_empty(self):
        tps = self.proxy.translation_pattern.list
        self.assertTrue(tps)

    def test_2_istances(self):
        tps = self.proxy.translation_pattern.list
        self.assertTrue(all(isinstance(tp, CSVTranslationPattern) for tp in tps))

    def test_3_discard_digits(self):
        tps = self.proxy.translation_pattern.list
        discard_digits = set(tp.discard_digits for tp in tps)
        print(', '.join(f'"{dd}"' for dd in discard_digits))

    def test_4_pre_dot_tps(self):
        """
        Not really a test: print a list of TPs w/ "PreDot" digit discard instruction
        :return:
        """
        tps = [tp
               for tp in self.proxy.translation_pattern.list
               if tp.discard_digits == 'PreDot']
        for tp in tps:
            print(f'{tp.pattern} prefix: {tp.called_party_prefix_digits} mask: {tp.called_party_mask}')


class TestTp(TestCase):
    def setUp(self) -> None:
        super(TestTp, self).setUp()
        logging.basicConfig(level=logging.DEBUG)
        logging.getLogger('digit_analysis.base').setLevel(logging.DEBUG)

    def test_translate_2234_to_1234(self):
        tp = TranslationPattern(pattern='2XXX',
                                css=['translated'],
                                called_party_mask='1XXX')
        translated, css = tp.translate(digits='2234', css='in')
        self.assertEqual(translated, '1234')
        self.assertEqual(css, 'translated')

    def test_translate_2345_to_1234_no_X_in_mask(self):
        tp = TranslationPattern(pattern='2XXX',
                                css=['translated'],
                                called_party_mask='1234')
        translated, css = tp.translate(digits='2345', css='in')
        self.assertEqual(translated, '1234')
        self.assertEqual(css, 'translated')

    def test_translate_ESN_to_e164(self):
        tp = TranslationPattern(pattern='84969XXX',
                                css=['translated'],
                                called_party_mask='+4961007739XXX',
                                use_originators_calling_search_space=True)
        translated, css = tp.translate(digits='84969764', css='in')
        self.assertEqual(translated, '+4961007739764')
        self.assertEqual(css, 'in')

    def test_translate_pre_dot(self):
        tp = TranslationPattern(pattern='000.49!',
                                css=['translated'],
                                discard_digits='PreDot',
                                use_originators_calling_search_space=True)
        translated, css = tp.translate(digits='000491', css='in')
        self.assertEqual(translated, '491')
        self.assertEqual(css, 'in')

    def test_translate_pre_dot_prefix(self):
        tp = TranslationPattern(pattern='000.49!',
                                css=['translated'],
                                discard_digits='PreDot',
                                called_party_prefix_digits='+',
                                use_originators_calling_search_space=True)
        translated, css = tp.translate(digits='000491', css='in')
        self.assertEqual(translated, '+491')
        self.assertEqual(css, 'in')

    def test_missing_dot(self):
        tp = TranslationPattern(pattern='00049!',
                                css=['translated'],
                                discard_digits='PreDot',
                                called_party_prefix_digits='+',
                                use_originators_calling_search_space=True)
        self.assertRaises(TranslationError, lambda: tp.translate(digits='000491', css='in'))

    def test_pre_dot_with_mask(self):
        tp = TranslationPattern(pattern='000.49!',
                                css=['translated'],
                                discard_digits='PreDot',
                                called_party_mask='XX',
                                use_originators_calling_search_space=False)
        translated, css = tp.translate(digits='000491', css='in')
        self.assertEqual('91', translated)
        self.assertEqual(css, 'translated')

    def test_transform_wildcard_set(self):
        tp = TranslationPattern(pattern='1.234XX',
                                css=['translated'],
                                discard_digits='PreDot',
                                called_party_mask='XXXXX')
        translated, css = tp.translate(digits='123456', css='in')
        self.assertEqual(css, 'translated')
        self.assertEqual(translated, '23456')

    def test_transform_wildcard_set_1(self):
        tp = TranslationPattern(pattern='1.234XX',
                                css=['translated'],
                                discard_digits='PreDot',
                                called_party_mask='XXX')
        translated, css = tp.translate(digits='123456', css='in')
        self.assertEqual(css, 'translated')
        self.assertEqual(translated, '456')

    def test_transform_wildcard_digit_string(self):
        tp = TranslationPattern(pattern='1.234XX',
                                css=['translated'],
                                discard_digits='PreDot',
                                called_party_mask='XXX')
        translated, css = tp.translate(digits='123X[14-69]X', css='in')
        self.assertEqual(css, 'translated')
        self.assertEqual(translated, 'X[14569]X')
