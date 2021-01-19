from .base import *

from typing import List

__all__ = ['Rdp', 'RdpContainer']


class Rdp(ObjBase):
    @property
    def name(self) -> str:
        return self.remote_destination_profile_name

    @property
    def description(self) -> str:
        return self.dict['DESCRIPTION']

    @property
    def mobility_user(self) -> str:
        return self.mobility_user_id

    @property
    def device_pool(self) -> str:
        return self.dict['DEVICE POOL']

    @property
    def css(self) -> str:
        return self.dict['CSS']

    pass


class RdpContainer(CsvBase):
    factory = Rdp

    @property
    def list(self) -> List[Rdp]:
        return super(RdpContainer, self).list
