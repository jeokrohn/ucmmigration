from .base import *
from .linegroup import LineGroupContainer

from re import compile
from typing import Dict, List, Set
from itertools import chain

from .phone import Phone, PhoneContainer

__all__ = ['HuntList', 'HuntListContainer', 'HuntListMember']


class HuntListMember(ObjBase):

    @property
    def selection_order(self) -> int:
        return int(self.dict['SELECTION ORDER'])

    @property
    def line_group(self) -> str:
        return self.dict['LINE GROUP']

    def __str__(self):
        return f'{self.selection_order}:{self.line_group}'


class HuntList(ObjBase):
    attribute_pattern = compile(r'(.+) (\d+)')

    def __init__(self, o: Dict):
        super(HuntList, self).__init__(o)
        self._members = None

    @property
    def name(self) -> str:
        return self.dict['NAME']

    def __str__(self):
        return self.name

    @property
    def description(self) -> str:
        return self.dict['DESCRIPTION']

    @property
    def enabled(self) -> bool:
        return self.route_list_enabled

    @property
    def for_vm(self) -> bool:
        return self.huntlist_for_vm

    @property
    def members(self) -> List[HuntListMember]:
        member_index = None
        members = []
        keys_to_remove = []
        if self._members is None:
            for k, v in self.dict.items():
                if m := self.attribute_pattern.match(k):
                    if REMOVE_ATTR_FROM_PARENT:
                        keys_to_remove.append(k)
                    attribute = m.group(1)
                    index = int(m.group(2))
                    if member_index != index:
                        members.append({attribute: v})
                        member_index = index
                    else:
                        members[-1][attribute] = v
            self._members = [HuntListMember(m) for m in members if m['SELECTION ORDER']]
            d = self.dict
            for k in keys_to_remove:
                d.pop(k)
        return self._members

    def pattern_and_partition_set(self, hunt_list_container: 'HuntListContainer') -> Set[str]:
        """
        All pattern:partition values in all line groups of the hunt list
        :return: set of pattern:partition strings
        """
        line_groups = set(m.line_group for m in self.members)
        lg_container = hunt_list_container.line_group_container
        r = set(chain.from_iterable(
            lg_container[line_group].pattern_and_partition_set()
            for line_group in line_groups))
        r1 = set()
        for line_group in line_groups:
            r1 |= lg_container[line_group].pattern_and_partition_set()
        return r

    def phones(self, hunt_list_container: 'HuntListContainer', phone_container: PhoneContainer) -> Set[Phone]:
        """
        All phones on which one of the DNPs is present
        """
        members = self.pattern_and_partition_set(hunt_list_container=hunt_list_container)
        return set(chain.from_iterable(phone_container.by_dn_and_partition.get(dnp, []) for dnp in members))


class HuntListContainer(CsvBase):
    factory = HuntList

    def __init__(self, tar: str, line_group_container: LineGroupContainer):
        super(HuntListContainer, self).__init__(tar)
        self.line_group_container = line_group_container

    def __getitem__(self, item) -> HuntList:
        try:
            r = self.by_name[item][0]
        except KeyError:
            foo = 1
        return r

    @property
    def list(self) -> List[HuntList]:
        return super(HuntListContainer, self).list
