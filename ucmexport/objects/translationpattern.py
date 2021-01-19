import re
from .base import *

from typing import List

__all__ = ['TranslationPattern', 'TranslationPatternContainer', 'TP_UNLIMITED']

TP_UNLIMITED = 100

class TranslationPattern(ObjBase):

    @property
    def pattern(self) -> str:
        return self.translation_pattern

    @property
    def partition(self) -> str:
        return self.route_partition

    @property
    def pattern_and_partition(self) -> str:
        return f'{self.pattern}:{self.partition}'

    @property
    def urgent(self) -> bool:
        return self.urgent_priority

    @property
    def css(self) -> str:
        return self.calling_search_space

    @property
    def use_originators_calling_search_space(self) -> bool:
        return self.use_originator_s_calling_search_space

    @property
    def route_option(self) -> str:
        return self.__getattr__('route_option')

    @property
    def block(self):
        """
        Blocking Pattern
        :return:
        """
        return self.route_option

    @property
    def block_pattern_option(self) -> bool:
        """
        Block option for blocking pattern
        :return:
        """
        return self.block_this_pattern_option

    @property
    def discard_digits(self) -> str:
        """
        Digit Discard Instruction
        :return:
        """
        return self.__getattr__('discard_digits')

    @property
    def called_party_mask(self) -> str:
        return self.called_party_transform_mask

    @property
    def called_party_prefix_digits(self) -> str:
        return self.called_party_prefix_digits__outgoing_calls

    @property
    def route_next_hop_by_calling_party_number(self) -> bool:
        return self.__getattr__('route_next_hop_by_calling_party_number')

    def __str__(self):
        return self.pattern_and_partition

    @property
    def length(self) -> int:
        """
        Determine length of digit string matched by TP
        :return:
        """
        p = self.pattern
        if p.endswith('!'):
            return TP_UNLIMITED
        # remove separator
        p = p.replace('.', '')
        # replace [..] with a single X
        p = re.sub(r'\[[0-9\-]+\]', 'X', p)
        return len(p)

    @property
    def translated_length(self) -> int:
        """
        Length of pattern after translation
        :return:
        """
        if self.called_party_mask:
            return len(self.called_party_mask)
        if (pattern_length := self.length) == TP_UNLIMITED:
            return TP_UNLIMITED
        if self.discard_digits == 'PreDot':
            pattern_length -= self.pattern.index('.')
        return pattern_length + len(self.called_party_prefix_digits)


class TranslationPatternContainer(CsvBase):
    factory = TranslationPattern

    @property
    def list(self) -> List[TranslationPattern]:
        return super(TranslationPatternContainer, self).list
