from .base import *

from collections import defaultdict
from re import compile, match
import itertools

from typing import List, Dict, Iterable, Set

__all__ = ['Phone', 'PhoneContainer', 'BusyLampField', 'SpeedDial', 'Line', 'Uri', 'PhoneDict']


class Uri(ObjBase):
    """
    URI information on a line
    """

    @property
    def uri(self):
        return self.on_directory_number

    @property
    def route_partition(self):
        return self.route_partition_on_directory_number

    def __str__(self):
        return f'{self.uri}:{self.route_partition}'


URI_PATTERN = compile(r'URI (\d) (.+)')


class Line(ObjBase):
    """
    a line on a phone
    """

    def __init__(self, o: Dict):
        super(Line, self).__init__(o)
        self._uris = None

    def __str__(self):
        return f'{self.directory_number}:{self.route_partition}'

    @property
    def directory_number(self) -> str:
        return self.__getattr__('directory_number')

    @property
    def partition(self) -> str:
        return self.route_partition

    @property
    def dn_and_partition(self) -> str:
        return f'{self.directory_number}:{self.partition}'

    @property
    def external_phone_number_mask(self) -> str:
        return self.__getattr__('external_phone_number_mask')

    @property
    def css(self) -> str:
        return self.line_css

    @property
    def aar_group(self) -> str:
        return self.aar_group_line

    @property
    def call_pickup_group(self) -> str:
        return self.__getattr__('call_pickup_group')

    @property
    def uris(self) -> Dict[int, Uri]:
        if self._uris is None:
            # collect uri information
            uris: Dict[int, Dict] = defaultdict(dict)
            remove_keys = []
            for k, v in self.dict.items():
                if k.startswith('URI '):
                    if REMOVE_ATTR_FROM_PARENT:
                        remove_keys.append(k)
                    uri_index = k.split(' ')[1]
                    attribute = k[5 + len(uri_index):]
                    uris[uri_index][attribute] = v
            d = self.dict
            for k in remove_keys:
                d.pop(k)
            self._uris = {int(k): Uri(uri) for k, uri in uris.items() if uri['ON DIRECTORY NUMBER']}
        return self._uris


SD_PATTERN = compile(r'SPEED DIAL (\w+) (\d+)')


class SpeedDial(ObjBase):
    @property
    def label(self):
        return self.dict['LABEL']

    @property
    def number(self):
        return self.dict['NUMBER']

    def __str__(self):
        return f'{self.label}:{self.number}'


BLF_PATTERN = compile(r'BUSY LAMP FIELD (.+) (\d+)')


class BusyLampField(ObjBase):
    def __init__(self, o: Dict):
        super(BusyLampField, self).__init__(o)
        dn = self.dict['DIRECTORY NUMBER']
        if dn and (m := match(r'(\d+) in (\D+)', dn)):
            # noinspection PyUnboundLocalVariable
            self._dn = m.group(1)
            self._partition = m.group(2)
        else:
            self._dn = ''
            self._partition = ''

    @property
    def label(self) -> str:
        return self.__getattr__('label')

    @property
    def destination(self) -> str:
        return self.__getattr__('destination')

    @property
    def directory_number(self) -> str:
        return self._dn

    @property
    def partition(self) -> str:
        return self._partition

    @property
    def dn_and_partition(self) -> str:
        return f'{self.directory_number}:{self.partition}'

    @property
    def call_pickup(self) -> bool:
        return self.__getattr__('call_pickup')

    def __str__(self):
        return f'{self.label}:{self.destination}:{self.directory_number}:{self.call_pickup}'


ATTRIBUTE_PATTERN = compile(r'(.+) (\d+)')


class Phone(ObjBase):
    def __init__(self, o: Dict):
        super(Phone, self).__init__(o)
        self._lines = None
        self._speed_dials = None
        self._blfs = None
        self._user_ids = None

    @property
    def lines(self) -> Dict[int, Line]:
        if self._lines is None:
            line = None
            line_index = None
            lines = dict()
            remove_keys = []
            line_index_len = None
            for k, v in self.dict.items():
                k: str
                # look for 'Directory Number" and 'Speed Dial'
                if (k[0] in 'DS') and \
                        ((sd := k.startswith('DIRECTORY N')) or k.startswith('SPEE')):
                    # end collecting the current line
                    if line is not None:
                        # collect the line
                        lines[int(line_index)] = Line(line)
                        line = None
                    # noinspection PyUnboundLocalVariable
                    if sd and v:
                        # start a new line only if the directory number is not empty
                        line = dict()
                        line_index = k.split(' ')[-1]
                        # index len including preceeding space
                        line_index_len = len(line_index) + 1
                    elif not sd:
                        # we are done as soon as we hit the 1st Speed Dial
                        break
                    else:
                        line = None

                if line is not None:
                    # remove this key from phone
                    if REMOVE_ATTR_FROM_PARENT:
                        remove_keys.append(k)
                    # add an attribute to the line
                    # attribute is all up to the line index
                    k = k[:-line_index_len]
                    line[k] = v

            if line is not None:
                # store the line
                lines[int(line_index)] = Line(line)
            self._lines = lines
            d = self.dict
            for k in remove_keys:
                d.pop(k)
        return self._lines

    @property
    def speed_dials(self) -> Dict[int, SpeedDial]:
        if self._speed_dials is None:
            keys_to_delete = []
            speed_dials = defaultdict(dict)
            for k, v in self.dict.items():
                if not k.startswith('SPEED '):
                    continue
                if m := SD_PATTERN.match(k):
                    if REMOVE_ATTR_FROM_PARENT:
                        keys_to_delete.append(k)
                    attribute = m.group(1)
                    index = int(m.group(2))
                    speed_dials[index][attribute] = v
            self._speed_dials = {k: SpeedDial(v) for k, v in speed_dials.items() if v['NUMBER']}
            d = self.dict
            for k in keys_to_delete:
                d.pop(k)
        return self._speed_dials

    @property
    def busy_lamp_fields(self) -> Dict[int, BusyLampField]:
        if self._blfs is None:
            blfs = defaultdict(dict)
            keys_to_delete = []
            for k, v in self.dict.items():
                if not k.startswith('BUSY'):
                    continue
                if m := BLF_PATTERN.match(k):
                    if REMOVE_ATTR_FROM_PARENT:
                        keys_to_delete.append(k)
                    attribute = m.group(1)
                    index = int(m.group(2))
                    blfs[index][attribute] = v
            self._blfs = {k: BusyLampField(v) for k, v in blfs.items() if
                          v['DESTINATION'] or v['DIRECTORY NUMBER'] or v['CALL PICKUP']}
            d = self.dict
            for k in keys_to_delete:
                d.pop(k)
        return self._blfs

    def __str__(self):
        return self.device_name

    def __lt__(self, other):
        return str(self) < str(other)

    @property
    def device_name(self):
        return self.dict['DEVICE NAME']

    @property
    def device_pool(self):
        return self.dict['DEVICE POOL']

    @property
    def device_type(self):
        return self.dict['DEVICE TYPE']

    @property
    def css(self):
        return self.dict.get('CSS')

    @property
    def aar_css(self):
        return self.dict.get('AAR CSS')

    @property
    def location(self):
        return self.dict.get('LOCATION')

    @property
    def phone_button_template(self):
        return self.__getattr__('phone_button_template')

    @property
    def uris(self) -> Iterable[Uri]:
        return list(itertools.chain.from_iterable(line.uris.values() for line in self.lines.values()))

    @property
    def has_uri(self) -> bool:
        if list(self.uris):
            return True
        else:
            return False

    @property
    def owner(self) -> str:
        return self.owner_user_id

    def user_id(self, index: int) -> str:
        return self.__getattr__(f'user_id_{index}')

    @property
    def user_ids(self) -> List[str]:
        if self._user_ids is None:
            self._user_ids = []
            i = 1

            while True:
                try:
                    uid = self.user_id(i)
                    if not uid:
                        break
                    self._user_ids.append(uid)
                except AttributeError:
                    break
                i += 1
        return self._user_ids

    @property
    def user_set(self) -> Set[str]:
        """
        all user ids referenced on the phone: owner and USER ID X
        :return: set of user IDs
        """
        return set(u for u in itertools.chain([self.owner], self.user_ids) if u)


PhoneDict = Dict[str, List[Phone]]


class PhoneContainer(CsvBase):
    factory = Phone

    def __init__(self, tar: str):
        super(PhoneContainer, self).__init__(tar)
        self._line_related_patterns_and_partitions = None
        self._by_user_id = None
        self._by_dn_and_partition = None
        self._by_call_pickup_group = None

    @property
    def by_device_name(self) -> PhoneDict:
        return self.by_attribute('device_name')

    def __getitem__(self, item) -> Phone:
        return self.by_device_name[item][0]

    @property
    def list(self) -> List[Phone]:
        return super(PhoneContainer, self).list

    @property
    def by_device_type(self) -> PhoneDict:
        return self.by_attribute('device_type')

    @property
    def by_device_pool(self) -> PhoneDict:
        return self.by_attribute('device_pool')

    @property
    def by_owner(self) -> PhoneDict:
        return self.by_attribute('owner')

    @property
    def by_user_id(self) -> PhoneDict:
        """
        Phones indexed by user ids
        :return:
        """
        if self._by_user_id is None:
            d: PhoneDict = defaultdict(list)
            for phone in self.list:
                for user_id in phone.user_set:
                    d[user_id].append(phone)
            self._by_user_id = d
        return self._by_user_id

    def with_owner(self) -> Iterable[Phone]:
        p: Phone
        return (p for p in self.list if p.owner)

    def without_owner(self) -> Iterable[Phone]:
        p: Phone
        return (p for p in self.list if not p.owner)

    def with_uri(self) -> Iterable[Phone]:
        return (p for p in self.list if p.has_uri)

    @property
    def by_dn_and_partition(self) -> Dict[str, Set[Phone]]:
        """
        Get sets of phones indexed by dn:partition provisioned on these phones
        :return: dict of sets of phones indexed by dn:partition provisioned on these phones
        """
        if self._by_dn_and_partition is None:
            r = defaultdict(set)
            for phone in self.list:
                for line in phone.lines.values():
                    r[line.dn_and_partition].add(phone)
            self._by_dn_and_partition = dict(r)
        return self._by_dn_and_partition

    @property
    def by_call_pickup_group(self) -> Dict[str, Set[Phone]]:
        """
        Get sets of phones indexed by call pickup groups provisioned on lines of these phones
        :return: dict of sets of phones indexed by call pickup group name
        """
        if self._by_call_pickup_group is None:
            result = defaultdict(set)
            for phone in self.list:
                # DPGs on all lines; we skip lines w/ empty DPG
                cpgs = set(cpg
                           for line in phone.lines.values()
                           if (cpg := line.call_pickup_group))
                for cpg in cpgs:
                    result[cpg].add(phone)
            self._by_call_pickup_group = dict(result)
        return self._by_call_pickup_group

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
