from .base import *
from typing import List, Dict, Optional
import re

__all__ = ['EndUser', 'EndUserContainer']


class PrimaryExtension:
    def __init__(self, primary_extension):
        m = re.match(r'(\S+) in (.+)', primary_extension)
        if m is None:
            self.dn = primary_extension
            self.partition = ''
        else:
            self.dn = m.group(1)
            self.partition = m.group(2)

    def __str__(self):
        return f'{self.dn}:{self.partition}'

    def __repr__(self):
        return f'PrimaryExtension({self})'


class DeviceAssociation:
    def __init__(self, device_name, default_profile, description, type_association):
        self.device_name = device_name
        self.default_profile = default_profile
        self.description = description
        self.type_association = type_association

    def __str__(self):
        return self.device_name

    def __repr__(self):
        return f'DeviceAssociation({self})'


class EndUser(ObjBase):
    def __init__(self, o: Dict):
        super(EndUser, self).__init__(o)
        self._primary_extensions = None
        self._device_associations = None

    def __str__(self):
        return self.user_id

    @property
    def first_name(self) -> str:
        return self.dict['FIRST NAME']

    @property
    def last_name(self) -> str:
        return self.__getattr__('last_name')

    @property
    def user_id(self) -> str:
        return self.__getattr__('user_id')

    @property
    def phone(self) -> str:
        return self.telephone_number

    @property
    def building(self) -> str:
        return self.__getattr__('building')

    @property
    def site(self) -> str:
        return self.__getattr__('site')

    @property
    def em_profile_name(self) -> Optional[str]:
        """
        extension mobility profile if available
        """
        return next((da.device_name
                     for da in self.device_associations
                     if da.type_association == 'Profile Available'), None)

    @property
    def primary_extensions(self) -> Dict[str, PrimaryExtension]:
        if self._primary_extensions is None:
            i = 0
            primary_extensions = dict()
            while True:
                i += 1
                try:
                    pe = self._obj.pop(f'PRIMARY EXTENSION {i}')
                    tpe = self._obj.pop(f'TYPE PATTERN USAGE {i}')
                except KeyError:
                    break
                if not pe:
                    break
                assert primary_extensions.get(tpe) is None
                primary_extensions[tpe] = PrimaryExtension(pe)
            self._primary_extensions = primary_extensions
        return self._primary_extensions

    @property
    def primary_extension(self) -> Optional[str]:
        return self.primary_extensions.get('Primary')

    @property
    def device_associations(self) -> List[DeviceAssociation]:
        if self._device_associations is None:
            device_associations = []
            i = 0
            while True:
                i += 1
                try:
                    dn = self._obj.pop(f'DEVICE NAME {i}')
                    dp = self._obj.pop(f'DEFAULT PROFILE {i}')
                    desc = self._obj.pop(f'DESCRIPTION {i}')
                    tua = self._obj.pop(f'TYPE USER ASSOCIATION {i}')
                except KeyError:
                    break
                if not dn:
                    break
                device_associations.append(DeviceAssociation(dn, dp, desc, tua))
            self._device_associations = device_associations
        return self._device_associations

    @property
    def cti_controlled(self) -> List[DeviceAssociation]:
        return [da
                for da in self.device_associations
                if da.type_association == 'Cti Control In']


class EndUserContainer(CsvBase):
    factory = EndUser

    @property
    def list(self) -> List[EndUser]:
        return super(EndUserContainer, self).list

    @property
    def by_em_profile_name(self) -> Dict[str, List[EndUser]]:
        return self.by_attribute('em_profile_name')

    def __getitem__(self, item) -> EndUser:
        return self.by_user_id[item][0]
