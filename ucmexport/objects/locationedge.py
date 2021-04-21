from .base import *

from typing import List

__all__ = ['LocationEdge', 'LocationEdgeContainer']


class LocationEdge(ObjBase):

    def __str__(self):
        return f'{self.location}->{self.neighboring_location}'

    @property
    def location(self) -> str:
        return self.dict['LOCATION']

    @property
    def neighboring_location(self) -> str:
        return self.dict['NEIGHBORING LOCATION']

    @property
    def weight(self) -> int:
        return int(self.dict['WEIGHT'])

    @property
    def audio_bandwidth(self) -> int:
        return int(self.dict['AUDIO BANDWIDTH'])

    @property
    def video_bandwidth(self) -> int:
        return int(self.dict['VIDEO BANDWIDTH'])

    @property
    def immersive_video_bandwidth(self) -> int:
        return int(self.dict['IMMERSIVE VIDEO BANDWIDTH'])


class LocationEdgeContainer(CsvBase):
    factory = LocationEdge

    @property
    def list(self) -> List[LocationEdge]:
        return super().list
