from .base import *

from typing import Dict, List

__all__ = ['Css', 'CssContainer']


class Css(ObjBase):
    def __init__(self, o: Dict):
        super(Css, self).__init__(o)
        # get a list of partitions
        d = self.dict
        keys_to_delete = [k for k in d if k.startswith('ROUTE PARTITION ')]
        partitions = [p for p in (d[k] for k in keys_to_delete) if p]
        self._partitions = partitions
        for k in keys_to_delete:
            d.pop(k)

    def __str__(self):
        return self.name

    @property
    def name(self) -> str:
        return self.dict['NAME']

    @property
    def description(self) -> str:
        return self.dict['DESCRIPTION']

    @property
    def partition_usage(self) -> str:
        return self.type_of_partition_usage

    @property
    def partitions(self) -> List[str]:
        return self._partitions

    @property
    def partitions_string(self) -> str:
        return ':'.join(self.partitions)


class CssContainer(CsvBase):
    factory = Css

    @property
    def list(self) -> List[Css]:
        return super(CssContainer, self).list

    def __getitem__(self, item) -> Css:
        return self.by_name[item][0]

    def partition_names(self, css_name: str) -> List[str]:
        if css_name:
            return self[css_name].partitions
        else:
            return []
