from .base import *

from re import compile
from collections import defaultdict
from itertools import chain

from .phone import CommonPhoneAndDeviceProfileContainer, CommonPhoneAndDeviceProfile

from typing import Dict, List, Set

__all__ = ['LineGroup', 'LineGroupMember', 'LineGroupContainer']


class LineGroupMember(ObjBase):
    @property
    def selection_order(self) -> int:
        return int(self.line_selection_order)

    @property
    def dn_or_pattern(self) -> str:
        return self.dict['DN OR PATTERN']

    @property
    def partition(self) -> str:
        return self.route_partition

    @property
    def pattern_and_partition(self) -> str:
        return f'{self.dn_or_pattern}:{self.partition}'

    def __str__(self):
        return f'{self.pattern_and_partition}:{self.selection_order}'


ATTRIBUTE_PATTERN = compile(r'(.+) (\d+)')


class LineGroup(ObjBase):

    def __init__(self, o: Dict):
        super(LineGroup, self).__init__(o)
        self._members = None

    @property
    def name(self) -> str:
        return self.dict['NAME']

    @property
    def distribution_algorithm(self) -> str:
        return self.type_distribution_algorithm

    def __str__(self):
        return self.name

    @property
    def members(self) -> List[LineGroupMember]:
        if self._members is None:
            member_index = None
            keys_to_remove = []
            members = []
            for k, v in self.dict.items():
                if m := ATTRIBUTE_PATTERN.match(k):
                    if REMOVE_ATTR_FROM_PARENT:
                        keys_to_remove.append(k)
                    attribute = m.group(1)
                    index = int(m.group(2))
                    if member_index != index:
                        members.append({attribute: v})
                        member_index = index
                    else:
                        members[-1][attribute] = v
            self._members = [LineGroupMember(m) for m in members if m['DN OR PATTERN']]
            d = self.dict
            for k in keys_to_remove:
                d.pop(k)
        return self._members

    def pattern_and_partition_set(self) -> Set[str]:
        """
        All pattern:partition values in the line group
        :return: set of pattern:partition strings
        """
        return set([m.pattern_and_partition for m in self.members])

    def phones_or_device_profiles(self,
                                  container: CommonPhoneAndDeviceProfileContainer) -> Set[CommonPhoneAndDeviceProfile]:
        """
        All phones on which one of the DNPs is present
        """
        members = self.pattern_and_partition_set()
        return set(chain.from_iterable(container.by_dn_and_partition.get(dnp, []) for dnp in members))


class LineGroupContainer(CsvBase):
    factory = LineGroup

    def __init__(self, tar: str):
        super(LineGroupContainer, self).__init__(tar)
        self._related_patterns_and_partitions = None

    @property
    def list(self) -> List[LineGroup]:
        return super(LineGroupContainer, self).list

    def __getitem__(self, item) -> LineGroup:
        return self.by_name[item][0]

    def related_patterns_and_partitions(self) -> DNAandPartitionRelated:
        """
        Identify DN/partiton relations based on being members in the same line group
        :return:
        """
        if self._related_patterns_and_partitions is None:
            result = defaultdict(set)
            for line_group in self.list:
                pattern_and_partition_set = line_group.pattern_and_partition_set()
                for item in pattern_and_partition_set:
                    others = pattern_and_partition_set.copy()
                    others.remove(item)
                    if others:
                        result[item] |= others
            self._related_patterns_and_partitions = result
        return self._related_patterns_and_partitions
