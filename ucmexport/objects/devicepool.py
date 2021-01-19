from .base import *

from typing import Dict, List

__all__ = ['DevicePool', 'DevicePoolContainer']


class DevicePool(ObjBase):

    def __str__(self):
        return self.name

    @property
    def name(self):
        return self.device_pool_name

    @property
    def region(self):
        return self.dict['Region']

    @property
    def aar_css(self):
        return self.aar_calling_search_space

    @property
    def srst_reference(self):
        return self.dict['SRST REFÈRENCE']

    @property
    def geo_location(self):
        return self.dict['GEO LOCATION']

    @property
    def physical_location(self):
        return self.dict['PHYSICAL LOCATION']


class DevicePoolContainer(CsvBase):
    factory = DevicePool

    @property
    def list(self) -> List[DevicePool]:
        return super(DevicePoolContainer, self).list

    @property
    def by_name(self) -> Dict[str, List[DevicePool]]:
        return self.by_attribute('device_name')

    def __getitem__(self, item)->DevicePool:
        return self.by_name[item][0]
