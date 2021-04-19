from .base import *

from re import compile
import itertools
from .phone import CommonPhoneAndDeviceProfile, CommonPhoneAndDeviceProfileContainer
from typing import List, Dict, Iterable

__all__ = ['DeviceProfile', 'DeviceProfileContainer']

ATTRIBUTE_PATTERN = compile(r'(.+) (\d+)')


class DeviceProfile(CommonPhoneAndDeviceProfile):
    def __init__(self, o: Dict):
        super().__init__(o)

    def __str__(self):
        return self.device_profile_name

    @property
    def device_profile_name(self):
        return self.dict['DEVICE PROFILE NAME']


DPDict = Dict[str, List[DeviceProfile]]


class DeviceProfileContainer(CommonPhoneAndDeviceProfileContainer):
    factory = DeviceProfile

    def __init__(self, tar: str):
        super().__init__(tar)

    @property
    def by_dp_name(self) -> DPDict:
        return self.by_attribute('device_profile_name')

    def __getitem__(self, item) -> DeviceProfile:
        return self.by_dp_name[item][0]

    @property
    def list(self) -> List[DeviceProfile]:
        return super().list

    @property
    def by_device_type(self) -> DPDict:
        return super().by_device_type

    @property
    def by_user_id(self) -> DPDict:
        return super().by_user_id

    @property
    def by_dn_and_partition(self) -> DPDict:
        return super().by_dn_and_partition

    @property
    def by_call_pickup_group(self) -> DPDict:
        return super().by_call_pickup_group

    @property
    def by_login_user_id(self) -> DPDict:
        return self.by_attribute('login_user_id')

    def with_uri(self) -> Iterable[DeviceProfile]:
        return (p for p in self.list if p.has_uri)

    def related_lines(self) -> DNAandPartitionRelated:
        """
        Determine which DN:partitions are related b/c they exist on the same device
        :return: dictionary, key is DN:partition, values are set of DN:partition.
        Only contains DN:partition keys where there are actually related DN:partition values
        """
        return {dnp: others for dnp, phone_set in self.by_dn_and_partition.items()
                if (others := set(itertools.chain.from_iterable((line.dn_and_partition
                                                                 for line in p.lines.values()
                                                                 ) for p in phone_set)) - {dnp})}
