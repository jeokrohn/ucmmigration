from .base import *

from typing import List

__all__ = ['CallPark', 'CallParkContainer']


class CallPark(ObjBase):
    @property
    def number(self) -> str:
        return self.__getattr__('number')

    @property
    def partition(self) -> str:
        return self.route_partition

    @property
    def number_and_partition(self) -> str:
        return f'{self.number}:{self.partition}'

    @property
    def description(self) -> str:
        return self.__getattr__('description')

    @property
    def ucm(self)->str:
        return self.unified_callmanager

    def __str__(self):
        return self.number_and_partition


class CallParkContainer(CsvBase):
    factory = CallPark

    @property
    def list(self) -> List[CallPark]:
        return super(CallParkContainer, self).list
