from test.proxytestcase import ProxyTestCase
from ucmexport import PhoneButtonTemplate, Css, SpeedDial
from digit_analysis import DaNode, DnPattern
from itertools import chain

import logging

from typing import List


class TestPbt(ProxyTestCase):
    def test_1_list(self):
        pbts = self.proxy.phone_button_template.list
        self.assertIsInstance(pbts, list)

    def test_2_len(self):
        pbts = self.proxy.phone_button_template.list
        self.assertTrue(pbts)

    def test_3_pbt(self):
        pbts = self.proxy.phone_button_template.list
        self.assertTrue(all(isinstance(pbt, PhoneButtonTemplate) for pbt in pbts))

    def test_4_pbt_button_types(self):
        pbts = self.proxy.phone_button_template.list
        feature_types = sorted(list(set(chain.from_iterable((button.feature_type
                                                             for button in pbt.buttons)
                                                            for pbt in pbts))))
        self.assertTrue(feature_types)
        print(f'Phone button template feature types: {", ".join(feature_types)}')


class TestPbtAndPhone(ProxyTestCase):

    def setUp(self) -> None:
        super(TestPbtAndPhone, self).setUp()
        logging.getLogger('digit_analysis.node.match').setLevel(logging.INFO)

    def test_sd_blf(self):
        # prepare DA lookup
        da_tree = DaNode.from_proxy(self.proxy)

        # find phones with SD BLF
        pbt_w_sd_blf = [pbt
                        for pbt in self.proxy.phone_button_template.list
                        if any(button.feature_type == 'Speed Dial BLF'
                               for button in pbt.buttons)]
        phones_w_sd_blf = {pbt.name: phones
                           for pbt in pbt_w_sd_blf
                           if (phones := self.proxy.phones.by_phone_button_template.get(pbt.name))}
        for pbt, phones in phones_w_sd_blf.items():
            for phone in phones:
                # some speed dials are actually BLFs based on the phone button template
                pbt = self.proxy.phone_button_template.get(phone.phone_button_template)
                # all speed dials (or speed dial BLFs) in the phone button template
                pbt_sds = (button
                           for button in pbt.buttons
                           if button.feature_type.startswith('Speed Dial'))
                # Indices of speed dial BLFs in the list of speed dials
                sd_blf_indices = (i
                                  for i, sd in enumerate(pbt_sds, start=1)
                                  if sd.feature_type == 'Speed Dial BLF')
                # use these indices to pick the speed dials from the phone
                # no all SD BLS in the PBT might actually be set on the phone
                sd_blfs: List[SpeedDial]
                sd_blfs = [speed_dial
                           for sd_index in sd_blf_indices
                           if (speed_dial := phone.speed_dials.get(sd_index))]
                # css

                phone_css = phone.css
                if phone_css:
                    phone_css = self.proxy.css.get(phone_css)
                    self.assertIsNotNone(phone_css)
                    phone_css = phone_css.partitions_string
                else:
                    phone_css = ''
                line_css = phone.lines[1].css
                if line_css:
                    line_css = self.proxy.css.get(line_css)
                    self.assertIsNotNone(line_css)
                    line_css = line_css.partitions_string
                else:
                    line_css = ''
                effective_css = ':'.join([line_css, phone_css])
                for sd_blf in sd_blfs:
                    # noinspection PyTypeChecker
                    lookup = da_tree.lookup(digits=sd_blf.number,
                                            css=effective_css)
                    print(f'Da lookup for SD BLF "{sd_blf}" yields: "{lookup}"')
                    self.assertIsNotNone(lookup)
                    self.assertIsInstance(lookup, DnPattern)
                    lookup: DnPattern
                    phones_with_dn = self.proxy.phones.by_dn_and_partition.get(lookup.dn_and_partition)
                    self.assertTrue(phones_with_dn)
                    users = set(chain.from_iterable(phone.user_set for phone in phones_with_dn))
                    self.assertTrue(users)
                    print(f'Users with phones with that DN: {", ".join(users)}')
            # for
        # for

    def test_intercom(self):
        """
        Not really a test: just trying to identify phones using a phone button template with an intercom line
        :return:
        """
        # PBTs with at least one Intercom button
        pbts = [pbt
                for pbt in self.proxy.phone_button_template.list
                if any(button.feature_type=='Intercom' for button in pbt.buttons)]
        print(f'Found {len(pbts)} phone button templates with intercom: {", ".join(f"{pbt}" for pbt in pbts)}')
        for pbt in pbts:
            phones_w_pbt = self.proxy.phones.by_phone_button_template.get(pbt.name, [])
            print(f'{pbt}: {len(phones_w_pbt)} phones: {", ".join(f"{phone}" for phone in phones_w_pbt)}')

