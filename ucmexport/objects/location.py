from .base import *

from typing import Dict, List, Set
from dataclasses import dataclass

__all__ = ['Location', 'LocationContainer']


@dataclass
class AssociatedLocation:
    location: str
    rsvp_setting: str


class Location(ObjBase):

    def __init__(self, o: Dict):
        super().__init__(o)
        self._ass_loc: List[AssociatedLocation] = None

    def __str__(self):
        return self.name

    @property
    def name(self) -> str:
        return self.dict['NAME']

    @property
    def audio_bandwidth(self) -> int:
        return int(self.dict['AUDIO BANDWIDTH'])

    @property
    def video_bandwidth(self) -> int:
        return int(self.dict['VIDEO BANDWIDTH'])

    @property
    def immersive_video_bandwidth(self) -> int:
        return int(self.dict['IMMERSIVE VIDEO BANDWIDTH'])

    @property
    def associated_locations(self) -> List[AssociatedLocation]:
        if self._ass_loc is None:
            ass_loc = []
            i = 1
            while True:
                location = self.dict.get(f'ASSOCIATED LOCATION {i}')
                if location is None:
                    break
                if location:
                    rsvp_setting = self.dict.get(f'RSVP SETTING {i}')
                    ass_loc.append(AssociatedLocation(location=location, rsvp_setting=rsvp_setting))
                i += 1
            self._ass_loc = ass_loc
        return self._ass_loc


class LocationContainer(CsvBase):
    factory = Location

    @property
    def list(self) -> List[Location]:
        return super().list
