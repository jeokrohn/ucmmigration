# Digit analysis tests
from unittest import TestCase
from digit_analysis import DaNode, DnPattern, TranslationPattern, RoutePattern
from digit_analysis.node import MAX_TRANSLATION_DEPTH

from itertools import chain
from collections import Counter
import re

class TestDp(TestCase):
    DNS = [
        '\\+14085551001', '\\+14085551002', '\\+14085551005', '\\+14085551010', '\\+14085551011', '\\+14085551021',
        '\\+14085551022',
        '\\+19195551001', '\\+19195551002', '\\+19195551005', '\\+19195551099'
    ]

    TPS = [
        ('SJC', '10XX', '+14085551XXX'),
        ('RTP', '10XX', '+19195551XXX'),
        ('DN', '\\+19195551XXX', '+19195551002'),
        ('RTP', '5XXX', '+19195551005'),
        ('RTP', '51XX', '+19195551099'),
        ('FREAKTP', '9001', '9002'),
        ('FREAKTP', '9002', '9003'),
        ('FREAKTP', '9003', '9004'),
        ('FREAKTP', '9004', '9005'),
        ('FREAKTP', '9005', '9006'),
        ('FREAKTP', '9006', '9007'),
        ('FREAKTP', '9007', '9008'),
        ('FREAKTP', '9008', '5001')
    ]

    RPS = [
        ('RP1', '5XXX'),
        ('RP2', '5XXX')
    ]

    @classmethod
    def setUpClass(cls) -> None:
        cls.da_tree = DaNode()
        for dn in cls.DNS:
            dn_pattern = DnPattern(pattern=dn, partition='DN')
            cls.da_tree.add_pattern(dn_pattern)
        for partition, pattern, called_party_transform in cls.TPS:
            tp = TranslationPattern(pattern=pattern,
                                    partition=partition,
                                    use_originators_calling_search_space=True,
                                    called_party_mask=called_party_transform)
            cls.da_tree.add_pattern(tp)
        for partition, pattern in cls.RPS:
            rp = RoutePattern(pattern=pattern, partition=partition)
            cls.da_tree.add_pattern(rp)

    def test_lookup_1001_sjc(self):
        css = 'DN:SJC'
        lookup_result = self.da_tree.lookup(digits='1001', css=css)
        self.assertIsNotNone(lookup_result)
        self.assertEqual(len(lookup_result), 1)
        lookup_result = lookup_result[0]
        self.assertIsInstance(lookup_result, DnPattern)
        self.assertEqual(lookup_result.partition, 'DN')
        self.assertEqual(lookup_result.pattern, '\\+14085551001')

    def test_lookup_1003_sjc(self):
        """
        Dialing 1003 in SJC should fail b/c after translation there is no DN ...1003
        :return:
        """
        css = 'DN:SJC'
        lookup_result = self.da_tree.lookup(digits='1003', css=css)
        self.assertIsInstance(lookup_result, list)
        self.assertFalse(lookup_result)

    def test_lookup_1001_existing_dn(self):
        css = 'DN:RTP'
        for numeric_digits in [1001, 1002, 1005, 1099]:
            digits = str(numeric_digits)
            lookup_result = self.da_tree.lookup(digits=digits, css=css)
            self.assertIsNotNone(lookup_result)
            self.assertEqual(len(lookup_result), 1)
            lookup_result = lookup_result[0]
            self.assertIsInstance(lookup_result, DnPattern)
            self.assertEqual(lookup_result.partition, 'DN')
            self.assertEqual(lookup_result.pattern, f'\\+1919555{digits}')

    def test_lookup_1003_rtp(self):
        css = 'DN:RTP'
        lookup_result = self.da_tree.lookup(digits='1003', css=css)
        self.assertIsNotNone(lookup_result)
        self.assertEqual(len(lookup_result), 1)
        lookup_result = lookup_result[0]
        self.assertIsInstance(lookup_result, DnPattern)
        self.assertEqual(lookup_result.partition, 'DN')
        self.assertEqual(lookup_result.pattern, '\\+19195551002')

    def test_lookup_5101_rtp(self):
        css = 'DN:RTP'
        lookup_result = self.da_tree.lookup(digits='5101', css=css)
        self.assertIsNotNone(lookup_result)
        self.assertEqual(len(lookup_result), 1)
        lookup_result = lookup_result[0]
        self.assertIsInstance(lookup_result, DnPattern)
        self.assertEqual(lookup_result.partition, 'DN')
        self.assertEqual(lookup_result.pattern, '\\+19195551099')

    def test_lookup_incomplete_dn(self):
        css = 'DN:SJC'
        # dialing an incomplete dial string should fail
        lookup_result = self.da_tree.lookup(digits='+1408555', css=css)
        self.assertIsInstance(lookup_result, list)
        self.assertFalse(lookup_result)

    def test_matching_nodes_1099(self):
        css = 'DN:RTP'
        # dialing should give us two DA Nodes
        matches = list(self.da_tree.matching_nodes(digits='+19195551099', css=css))
        self.assertEqual(len(matches), 2)
        # sort by quality
        matches.sort(key=lambda x: x[1])
        self.assertEqual(matches[0][0].full_representation, '+19195551099')
        self.assertEqual(matches[1][0].full_representation, '+19195551XXX')

    def test_partition_order(self):
        lookup_result = self.da_tree.lookup(digits='5001', css='RP1:RP2')
        self.assertIsNotNone(lookup_result)
        self.assertEqual(len(lookup_result), 1)
        lookup_result = lookup_result[0]
        self.assertIsInstance(lookup_result, RoutePattern)
        self.assertEqual(lookup_result.partition, 'RP1')
        self.assertEqual(lookup_result.pattern, '5XXX')

        lookup_result = self.da_tree.lookup(digits='5001', css='RP2:RP1')
        self.assertIsNotNone(lookup_result)
        self.assertEqual(len(lookup_result), 1)
        lookup_result = lookup_result[0]
        self.assertIsInstance(lookup_result, RoutePattern)
        self.assertEqual(lookup_result.partition, 'RP2')
        self.assertEqual(lookup_result.pattern, '5XXX')

    def test_tp_recursion(self):
        for i in range(MAX_TRANSLATION_DEPTH + 1):
            pre_transform = f'{9008 - i}'
            lookup_result = self.da_tree.lookup(digits=pre_transform, css='FREAKTP:RP2')
            self.assertIsInstance(lookup_result, list)
            if i < MAX_TRANSLATION_DEPTH:
                self.assertIsNotNone(lookup_result)
                self.assertEqual(len(lookup_result), 1)
                lookup_result = lookup_result[0]
                self.assertIsInstance(lookup_result, RoutePattern)
                self.assertEqual(lookup_result.partition, 'RP2')
                self.assertEqual(lookup_result.pattern, '5XXX')
            else:
                self.assertFalse(lookup_result)

    def test_terminal_nodes(self):
        patterns = list(chain(self.DNS,
                              (pattern for _, pattern, _ in self.TPS),
                              (pattern for _, pattern in self.RPS)))
        pattern_count = Counter(patterns)
        for node in self.da_tree.terminal_nodes():
            pattern = node.full_representation
            if pattern.startswith('+'):
                pattern = f'\\{pattern}'
            self.assertIsNotNone(pattern_count.get(pattern), f'No count for {pattern}')
            pattern_count[pattern] -= len(node.terminal_pattern)
        # is there any pattern count not zero
        pattern_count = {p: c
                         for p, c in pattern_count.items()
                         if c}
        self.assertFalse(pattern_count, f'Some pattern counts are not zero: {pattern_count}')

    def test_unique_terminal_nodes(self):
        node_set = set()
        repr_set = set()
        for node in self.da_tree.terminal_nodes():
            self.assertTrue(node not in node_set, f'{node} already in {node_set}')
            node_set.add(node)
            self.assertTrue(node.full_representation not in repr_set,
                            f'{node.full_representation} already in {repr_set}')

    def test_breadth_first_traversal_each_node_once(self):
        """
        Each node should only be traversed once
        :return:
        """
        nodes = set()
        for node in self.da_tree.breadth_first_traversal():
            self.assertTrue(node not in nodes, f'{node} already in {nodes}')
            nodes.add(node)


    def test_lookup_w_wildcards(self):
        lookup_result = self.da_tree.lookup(digits='10XX', css='SJC:DN')
        self.assertIsInstance(lookup_result, list)
        self.assertEqual(len(lookup_result), 7)
        # All patterns should be DNs
        not_dn = [dnp for dnp in lookup_result if not isinstance(dnp, DnPattern)]
        self.assertFalse(not_dn, f'Some lookup results are not DNs: {not_dn}')
        # All patterns should be in SJC number range
        sjc_re = re.compile(r'\\\+14085551\d{3}')
        dn_not_sjc = [dnp for dnp in lookup_result if not sjc_re.match(dnp.pattern)]
        self.assertFalse(dn_not_sjc, f'Some DNs are not in SJC: {dn_not_sjc}' )