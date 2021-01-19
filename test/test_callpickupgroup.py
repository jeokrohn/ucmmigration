from test.proxytestcase import ProxyTestCase
from ucmexport import Proxy, CallPickupGroup
from typing import Optional
from test import TAR_FILE
import logging


class TestPickupGroup(ProxyTestCase):

    def test_list(self):
        cpgs = self.proxy.call_pickup_group.list
        self.assertIsInstance(cpgs, list)
        self.assertGreater(len(cpgs), 0)
        for cpg in cpgs:
            self.assertIsInstance(cpg, CallPickupGroup, f'Not a CallPickupGroup: {cpg}')

    def test_at_least_one_cpg_has_associated_cpgs(self):
        cpgs = self.proxy.call_pickup_group.list
        self.assertTrue(any(cpg.associated_cpgs
                            for cpg in cpgs))

    def test_number_of_cpgs_with_associated_cpgs(self):
        cpgs = self.proxy.call_pickup_group.list
        with_associated_cpgs = [cpg for cpg in cpgs if cpg.associated_cpgs]
        print(f'{len(cpgs)} call pickup groups')
        print(f'{len(with_associated_cpgs)} call pickup groups with associated CPGs')

    def test_cpgs_wo_associated_cpgs(self):
        cpgs = self.proxy.call_pickup_group.list
        wo_assoc = [cpg
                    for cpg in cpgs
                    if not cpg.associated_cpgs]
        if not wo_assoc:
            return
        print(f'{len(wo_assoc)} CPGs w/o associated CPGs')
        for cpg in wo_assoc:
            print(f'{cpg.name} {cpg.number_and_partition}')

    def test_associated_cpgs(self):
        cpgs = self.proxy.call_pickup_group.list
        for cpg in cpgs:
            associated = set(cpg.associated_cpgs)
            if associated:
                self.assertIn(cpg.name, associated)
