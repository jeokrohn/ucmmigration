from .base import *

from typing import Dict, List

__all__ = ['DirectoryNumber', 'DirectoryNumberContainer']


class DirectoryNumber(ObjBase):
    @property
    def number(self) -> str:
        return self.directory_number

    @property
    def partition(self) -> str:
        return self.route_partition

    @property
    def number_and_partition(self) -> str:
        return f'{self.number}:{self.partition}'

    @property
    def call_pickup_group(self) -> str:
        return self.__getattr__('call_pickup_group')

    def __str__(self):
        return f'{self.number_and_partition}'


class DirectoryNumberContainer(CsvBase):
    factory = DirectoryNumber

    @property
    def by_number_partition(self) -> Dict[str, List[DirectoryNumber]]:
        return self.by_attribute('number_and_partition')

    @property
    def by_call_pickup_group(self) -> Dict[str, List[DirectoryNumber]]:
        return self.by_attribute('call_pickup_group')

    @property
    def list(self) -> List[DirectoryNumber]:
        return super(DirectoryNumberContainer, self).list

    def __getitem__(self, item) -> DirectoryNumber:
        return self.by_number_partition[item][0]
