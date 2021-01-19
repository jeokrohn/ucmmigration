from .base import *

from re import compile

from typing import List, Dict

__all__ = ['PhoneButtonTemplate', 'PhoneButtonTemplateContainer', 'PhoneButton', 'BLF_FEATURE_TYPES']

BLF_FEATURE_TYPES = ['Speed Dial BLF', 'Call Park BLF']


class PhoneButton(ObjBase):
    @property
    def feature_type(self) -> str:
        return self.type_of_feature

    @property
    def label(self) -> str:
        return self.dict['LABEL']

    @property
    def parameter(self) -> str:
        return self.dict['PARAMETER']

    @property
    def fixed_feature(self) -> bool:
        return self.isfixedfeature

    def __str__(self):
        return self.label


BUTTON_ATTRIBUTES = compile(r'(.+) (\d+)')


class PhoneButtonTemplate(ObjBase):
    def __init__(self, o: Dict):
        super(PhoneButtonTemplate, self).__init__(o)
        self._buttons = None

    @property
    def name(self) -> str:
        return self.dict['NAME']

    @property
    def number_of_buttons(self) -> int:
        return int(self.dict['NUMBER OF BUTTONS'])

    @property
    def model_type(self) -> str:
        return self.type_of_model

    @property
    def protocol_type(self) -> str:
        return self.type_of_protocol

    def __str__(self):
        return self.name

    @property
    def buttons(self) -> List[PhoneButton]:
        if self._buttons is None:
            items = iter(self.dict.items())
            buttons = []
            for k, v in items:
                k: str
                if BUTTON_ATTRIBUTES.match(k) is None:
                    continue
                if not v or v == 'None':
                    break
                button = dict()
                button[k[:k.rfind(' ')]] = v
                for _ in range(3):
                    k, v = next(items)
                    button[k[:k.rfind(' ')]] = v
                buttons.append(PhoneButton(button))
            self._buttons = buttons
        return self._buttons


class PhoneButtonTemplateContainer(CsvBase):
    factory = PhoneButtonTemplate

    @property
    def list(self) -> List[PhoneButtonTemplate]:
        return super(PhoneButtonTemplateContainer, self).list

    def __getitem__(self, item) -> PhoneButtonTemplate:
        return self.by_name[item][0]
