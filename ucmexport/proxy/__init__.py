from ucmexport.objects import *

from itertools import chain
from typing import List, Dict, Set


class Proxy:
    def __init__(self, tar: str):
        self.css = CssContainer(tar)
        self.device_pools = DevicePoolContainer(tar)
        self.directed_call_park = DirectedCallParkContainer(tar)
        self.directory_number = DirectoryNumberContainer(tar)
        self.end_user = EndUserContainer(tar)
        self.call_park = CallParkContainer(tar)
        self.call_pickup_group = CallPickupGroupContainer(tar)

        self.line_group = LineGroupContainer(tar)
        self.hunt_list = HuntListContainer(tar, self.line_group)
        self.hunt_pilot = HuntPilotContainer(tar, self.hunt_list)

        self.phone_button_template = PhoneButtonTemplateContainer(tar)
        self.phones = PhoneContainer(tar)
        self.rdp = RdpContainer(tar)
        self.remote_destination = RemoteDestinationContainer(tar)
        self.route_pattern = RoutePatternContainer(tar)
        self.translation_pattern = TranslationPatternContainer(tar)

        self._dn_partition_by_enduser = None

    def dn_partition_by_enduser(self) -> Dict[EndUser, Set[str]]:
        """
        get sets of dn:partitions by enduser by looking lines on phones owned by each user
        :return:
        """
        if self._dn_partition_by_enduser is None:
            self._dn_partition_by_enduser = \
                {user: dnp_set for user in self.end_user.list
                 if (dnp_set := set(chain.from_iterable((l.dn_and_partition
                                                         for l in p.lines.values()
                                                         )
                                                        for p in self.phones.by_owner.get(user.user_id, []))))}
        return self._dn_partition_by_enduser

    def phones_with_blf(self) -> Dict[str, List[Phone]]:
        phone_button_templates = self.phone_button_template.list

        def is_blf(pb: PhoneButton):
            return pb.feature_type in BLF_FEATURE_TYPES

        pbt_with_blf = [pbt for pbt in phone_button_templates if any(map(is_blf, pbt.buttons))]
        phones_by_button_template = self.phones.by_phone_button_template

        phones_w_blf = {pbt: phones for pbt in pbt_with_blf if
                        (phones := phones_by_button_template.get(pbt.name))}
        phones_w_blf: Dict[PhoneButtonTemplate, List[Phone]]
        return phones_w_blf
