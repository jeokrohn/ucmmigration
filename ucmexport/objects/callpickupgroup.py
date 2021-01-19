from .base import *

from re import compile
from typing import List

__all__ = ['CallPickupGroupContainer', 'CallPickupGroup']


class CallPickupGroup(ObjBase):
    @property
    def number(self) -> str:
        return self.cpg_number

    @property
    def name(self) -> str:
        return self.cpg_name

    @property
    def description(self) -> str:
        return self.__getattr__('description')

    @property
    def partition(self) -> str:
        return self.route_partition

    @property
    def number_and_partition(self):
        return f'{self.number}:{self.partition}'

    def __str__(self):
        return self.name

    @property
    def associated_cpgs(self) -> List[str]:
        return [v for k, v in self.dict.items() if k.startswith('ASSOC') and v]


class CallPickupGroupContainer(CsvBase):
    factory = CallPickupGroup

    @property
    def list(self) -> List[CallPickupGroup]:
        return super(CallPickupGroupContainer, self).list
