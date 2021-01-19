from .base import *

__all__ = ['RoutePattern', 'RoutePatternContainer']

from typing import List


class RoutePattern(ObjBase):
    @property
    def pattern(self) -> str:
        return self.route_pattern

    @property
    def partition(self) -> str:
        return self.route_partition

    @property
    def pattern_and_partition(self):
        return f'{self.pattern}:{self.partition}'

    def __str__(self):
        return self.pattern_and_partition


class RoutePatternContainer(CsvBase):
    factory = RoutePattern

    def __init__(self, tar: str):
        super(RoutePatternContainer, self).__init__(tar)
        self._list = None

    @property
    def list(self) -> List[RoutePattern]:
        if self._list is None:
            r = super(RoutePatternContainer, self).list
            r.sort(key=lambda v: v.pattern_and_partition)
            self._list = r
        return self._list

    def __getitem__(self, item) -> RoutePattern:
        return self.by_pattern_and_partition[item]
