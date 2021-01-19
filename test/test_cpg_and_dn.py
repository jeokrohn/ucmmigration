from test.proxytestcase import ProxyTestCase

import logging


class TestCpgAndDn(ProxyTestCase):

    def setUp(self) -> None:
        logging.basicConfig(level=logging.DEBUG)

    def test_dns(self):
        dirns = self.proxy.directory_number.list
        dirns_w_cpg = [dn for dn in dirns if dn.call_pickup_group]
        by_cpg = {cpg: dn_list
                  for cpg, dn_list in self.proxy.directory_number.by_call_pickup_group.items()
                  if cpg and len(dn_list) > 1}
        foo = 1
