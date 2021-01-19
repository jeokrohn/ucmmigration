from .base import *

from typing import List

__all__ = ['DirectedCallParkContainer', 'DirectedCallPark']


class DirectedCallPark(ObjBase):
    @property
    def number(self) -> str:
        return self.__getattr__('number')

    @property
    def partition(self)->str:
        return self.route_partition

    @property
    def number_and_partition(self)->str:
        return f'{self.number}:{self.partition}'

    @property
    def description(self) -> str:
        return self.__getattr__('description')

    def __str__(self):
        return self.number_and_partition


class DirectedCallParkContainer(CsvBase):
    factory = DirectedCallPark

    @property
    def list(self) -> List[DirectedCallPark]:
        return super(DirectedCallParkContainer, self).list
