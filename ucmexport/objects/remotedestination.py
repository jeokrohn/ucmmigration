from .base import *

from re import compile
from collections import defaultdict

from typing import Dict, List, Tuple

__all__ = ['RemoteDestination', 'RemoteDestinationContainer', 'Destination', 'Schedule']


class Schedule(ObjBase):
    @property
    def day_of_week(self) -> str:
        return self.dict['DAY OF WEEK']

    @property
    def start_time(self) -> str:
        return self.dict['START TIME']

    @property
    def end_time(self) -> str:
        return self.dict['END TIME']

    def __str__(self):
        return f'{self.day_of_week}:{self.start_time}:{self.end_time}'


ATTRIBUTE_PATTERN = compile(r'(.+) (\d+)')


class Destination(ObjBase):
    def __init__(self, o: dict):
        # sometimes route_partition seems to be a list
        if isinstance(rp := o['ROUTE PARTITION'], list):
            o['ROUTE PARTITION'] = rp[0]

        super(Destination, self).__init__(o)
        self._schedules = None

    @property
    def destination(self) -> str:
        return self.dict['DESTINATION']

    @property
    def associated_line_number(self) -> str:
        return self.dict['ASSOCIATED LINE NUMBER']

    @property
    def route_partition(self) -> str:
        return self.dict['ROUTE PARTITION']

    @property
    def line_number_and_partition(self) -> str:
        return f'{self.associated_line_number}:{self.route_partition}'

    def __str__(self):
        return f'{self.destination}:{self.line_number_and_partition}'

    @property
    def schedules(self) -> List[Schedule]:
        if self._schedules is None:
            schedules = []
            keys_do_delete = []
            schedule_index = None
            schedule = None
            for k, v in self.dict.items():
                if m := ATTRIBUTE_PATTERN.match(k):
                    if REMOVE_ATTR_FROM_PARENT:
                        keys_do_delete.append(k)
                    index = m.group(2)
                    attribute = m.group(1)
                    if index != schedule_index:
                        schedule_index = index
                        if schedule != None and schedule['DAY OF WEEK']:
                            schedules.append(Schedule(schedule))
                        schedule = dict()
                    schedule[attribute] = v
            if schedule and schedule['DAY OF WEEK']:
                schedules.append(Schedule(schedule))
            d = self.dict
            for k in keys_do_delete:
                d.pop(k)
            self._schedules = schedules
        return self._schedules


SCHEDULE_ATTRIBUTES = set(['DAY OF WEEK', 'START TIME', 'END TIME'])


class RemoteDestination(ObjBase):
    def __init__(self, o: Dict):
        # remotedestination.csv seems to have entries with issues.
        # Looks like some rows habe NULL in the "TIME ZONE"
        # column. In these rows all following columns need to be shifted left
        if o['TIME ZONE'] == 'NULL':
            # generator for all keys and values of o
            i = ((k, v) for k, v in o.items())
            # consume all keys until TIME_ZONE
            next(k for k, _ in i if k == 'TIME ZONE')
            prev_key = 'TIME ZONE'
            # iterate through remaining keys and values
            for k, v in i:
                o[prev_key] = v
                prev_key = k
            # delete last key (None)
            o.pop(prev_key)
        super(RemoteDestination, self).__init__(o)
        self._destinations = None

    @property
    def name(self) -> str:
        return self.dict['NAME']

    @property
    def remote_destinaton_profile(self) -> str:
        return self.dict['REMOTE DESTINATION PROFILE']

    def __str__(self):
        return self.name

    @property
    def destinations(self) -> List[Destination]:
        if self._destinations is None:
            destinations = []
            destination = None
            keys_to_remove = []
            for k, v in self.dict.items():
                if k.startswith('DESTINATION '):
                    # first column of a destination
                    if destination is not None:
                        destinations.append(Destination(destination))
                    destination = dict()
                if destination is not None:
                    # this is an attribute of a destination
                    m = ATTRIBUTE_PATTERN.match(k)
                    attribute = m.group(1)
                    if attribute in SCHEDULE_ATTRIBUTES:
                        # keep the indices; will be consumed later
                        attribute = k
                    destination[attribute] = v
                    if REMOVE_ATTR_FROM_PARENT:
                        keys_to_remove.append(k)
            if destination is not None:
                destinations.append(Destination(destination))
            d = self.dict
            for k in keys_to_remove:
                d.pop(k)
            self._destinations = destinations
        return self._destinations


class RemoteDestinationContainer(CsvBase):
    factory = RemoteDestination

    def __init__(self, tar: str):
        super(RemoteDestinationContainer, self).__init__(tar)
        self._by_line_number_and_partition = None

    @property
    def list(self) -> List[RemoteDestination]:
        return super(RemoteDestinationContainer, self).list

    @property
    def by_line_number_and_partition(self) -> Dict[str, List[Tuple[RemoteDestination, Destination]]]:
        if self._by_line_number_and_partition is None:
            result = defaultdict(list)
            for remote_destination in self.list:
                for destination in remote_destination.destinations:
                    result[destination.line_number_and_partition].append((remote_destination, destination))
            self._by_line_number_and_partition = result

        return self._by_line_number_and_partition
