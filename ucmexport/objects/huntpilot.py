from collections import defaultdict
from itertools import chain
from re import compile
from typing import List, Dict, Set

from .base import *
from .huntlist import HuntListContainer
from .phone import CommonPhoneAndDeviceProfileContainer, CommonPhoneAndDeviceProfile

__all__ = ['HuntPilot', 'HuntPilotContainer', 'HuntPilotHuntList']


class HuntPilotHuntList(ObjBase):
    @property
    def hunt_list(self) -> str:
        return self.dict['HUNT LIST']

    @property
    def external_number_mask(self) -> str:
        return self.dict['EXTERNAL NUMBER MASK']

    @property
    def max_callers(self) -> str:
        return self.maximum_number_of_callers_in_queue

    @property
    def destination_queue_full(self) -> str:
        return self.destination_when_queue_is_full

    @property
    def full_css(self) -> str:
        return self.full_queue_calling_search_space

    def __str__(self):
        return self.hunt_list


HUNT_LIST_PATTERN = compile(r'(.+) (\d+)')


class HuntPilot(ObjBase):
    def __init__(self, o: Dict):
        super(HuntPilot, self).__init__(o)
        self._hunt_lists = None

    @property
    def hunt_pilot(self) -> str:
        return self.dict['HUNT PILOT']

    @property
    def partition(self) -> str:
        return self.route_partition

    @property
    def description(self) -> str:
        return self.dict['DESCRIPTION']

    @property
    def pilot_and_partition(self) -> str:
        return f'{self.hunt_pilot}:{self.partition}'

    @property
    def routethis_pattern(self) -> bool:
        return self.dict['ROUTETHIS PATTERN'] == 't'

    def __str__(self):
        return self.pilot_and_partition

    @property
    def hunt_lists(self) -> List[HuntPilotHuntList]:
        if self._hunt_lists is None:
            hl_attrs = ((HUNT_LIST_PATTERN.match(k), k, v) for k, v in self.dict.items())
            hl_attrs = ((m.group(1), int(m.group(2)), k, v) for m, k, v in hl_attrs if m)
            hunt_lists = defaultdict(dict)
            keys_to_delete = []
            for attribute, index, k, v in hl_attrs:
                if REMOVE_ATTR_FROM_PARENT:
                    keys_to_delete.append(k)
                hunt_lists[index][attribute] = v
            self._hunt_lists = [HuntPilotHuntList(hl) for hl in hunt_lists.values()]
            d = self.dict
            for k in keys_to_delete:
                d.pop(k)
        return self._hunt_lists

    def pattern_and_partition_set(self, hunt_pilot_container: 'HuntPilotContainer') -> Set[str]:
        """
        All pattern:partition values in all line groups of all hunt list of the pilot
        :return: set of pattern:partition strings
        """
        hunt_lists = set(m.hunt_list for m in self.hunt_lists)
        hunt_list_container = hunt_pilot_container.hunt_list_container

        r = set(chain.from_iterable(
            hunt_list_container[hunt_list].pattern_and_partition_set(hunt_list_container=hunt_list_container)
            for hunt_list in hunt_lists
            if hunt_list))
        return r

    def phones_or_device_profiles(self, hunt_pilot_container: 'HuntPilotContainer',
                                  container: CommonPhoneAndDeviceProfileContainer) -> Set[CommonPhoneAndDeviceProfile]:
        """
        All phones or device profiles on which one of the DNPs is present
        """
        members = self.pattern_and_partition_set(hunt_pilot_container=hunt_pilot_container)
        return set(chain.from_iterable(container.by_dn_and_partition.get(dnp, []) for dnp in members))


class HuntPilotContainer(CsvBase):
    factory = HuntPilot

    def __init__(self, tar: str, hunt_list_container: HuntListContainer):
        super(HuntPilotContainer, self).__init__(tar)
        self.hunt_list_container = hunt_list_container

    def __getitem__(self, item) -> HuntPilot:
        """
        Get HuntPilot by hunt pilot name
        :param item: hunt pilot name
        :return: selected hunt Pilot
        """
        return self.by_hunt_pilot[item][0]

    @property
    def list(self) -> List[HuntPilot]:
        return super(HuntPilotContainer, self).list

    def pattern_and_partition_sets(self) -> Dict[str, Set[str]]:
        """
        pattern:partition sets for each huntpilot indexed by hunt pilot name
        :return:
        """
        r = {hp.hunt_pilot: hp.pattern_and_partition_set(hunt_pilot_container=self) for hp in self.list}
        return r

    def pilot_related_patterns_and_partitions(self) -> DNAandPartitionRelated:
        result: DNAandPartitionRelated = defaultdict(set)
        for dn_and_p_set in self.pattern_and_partition_sets().values():
            for dnp in dn_and_p_set:
                others = dn_and_p_set.copy()
                others.remove(dnp)
                if others:
                    result[dnp] |= others
        return result
