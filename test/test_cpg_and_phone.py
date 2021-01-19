from test.proxytestcase import ProxyTestCase


class TestCpgAndDn(ProxyTestCase):

    def test_by_cpg(self):
        by_cpg = self.proxy.phones.by_call_pickup_group
        self.assertTrue(by_cpg)

    def test_by_cpg_set(self):
        by_cpg = self.proxy.phones.by_call_pickup_group
        self.assertTrue(all(isinstance(phone_set, set)
                            for phone_set in by_cpg.values()))

    def test_by_cpg_set_len(self):
        by_cpg = self.proxy.phones.by_call_pickup_group
        self.assertTrue(all(phone_set
                            for phone_set in by_cpg.values()))

    def test_no_empty_cpg(self):
        by_cpg = self.proxy.phones.by_call_pickup_group
        self.assertIsNone(by_cpg.get(''))

    def test_dpgs_exist(self):
        by_cpg = self.proxy.phones.by_call_pickup_group.keys()
        cpg_names = set(cpg.name
                        for cpg in self.proxy.call_pickup_group.list)
        undefined_cpgs_names = [cpg_name
                                for cpg_name in by_cpg
                                if cpg_name not in cpg_names]
        self.assertFalse(undefined_cpgs_names,
                         f'CPGs used on phones but not defined in CPG csv: {", ".join(undefined_cpgs_names)}')
