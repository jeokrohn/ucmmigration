from enum import unique, Enum
from itertools import zip_longest
from typing import List, Tuple, Set
import logging

__all__ = ['PatternType', 'Pattern', 'TranslationPattern', 'DnPattern', 'RoutePattern', 'ALL_PATTERN_TYPES',
           'TranslationError']


@unique
class PatternType(Enum):
    DN = 0
    TP = 1
    RP = 2

    def __str__(self):
        return self.name


ALL_PATTERN_TYPES = {PatternType.DN, PatternType.TP, PatternType.RP}

log = logging.getLogger(__name__)


class Pattern:
    __slots__ = ['type', 'pattern', 'partition']

    def __init__(self, pattern: str, partition: str, type: PatternType):
        self.type = type
        self.pattern = pattern
        self.partition = partition

    def __str__(self):
        return f'{self.dn_and_partition}({self.type})'

    @property
    def dn_and_partition(self):
        partition = self.partition or 'NONE'
        return f'{self.pattern}:{partition}'


class TranslationError(Exception):
    pass


class TranslationPattern(Pattern):
    __slots__ = ['css', 'block', 'urgent', 'use_originators_calling_search_space', 'discard_digits',
                 'called_party_mask', 'called_party_prefix_digits', 'route_next_hop_by_calling_party_number']

    def __init__(self, pattern: str = '', partition: str = '', block: bool = False,
                 css: List[str] = None, urgent: bool = True, use_originators_calling_search_space: bool = False,
                 discard_digits: int = 0, called_party_mask: str = '', called_party_prefix_digits: str = '',
                 route_next_hop_by_calling_party_number: bool = False):
        super(TranslationPattern, self).__init__(pattern=pattern, partition=partition, type=PatternType.TP)
        self.css = css
        self.block = block
        self.urgent = urgent
        self.use_originators_calling_search_space = use_originators_calling_search_space
        self.discard_digits = discard_digits
        self.called_party_mask = called_party_mask
        self.called_party_prefix_digits = called_party_prefix_digits
        self.route_next_hop_by_calling_party_number = route_next_hop_by_calling_party_number

    def translate(self, digits: str, css: str) -> Tuple[str, str]:
        """
        Apply translation to given digit string
        :param digits: digit string
        :param css: activating css
        :return: Tuple[digit string, css for secondary lookup]
        """

        def discard_digits(digits: str) -> str:
            # find dot in pattern
            dot_pos = self.pattern.find('.')
            if dot_pos == -1:
                raise TranslationError(f'discard PreDot requires "." in pattern: {self}')
            return digits[dot_pos:]

        def str_to_set_list(digits: str) -> List[Set[str]]:
            digits = iter(digits)
            result = []
            for digit in digits:
                if digit == '[':
                    # start of enumeration
                    dset = set()
                    p_digit = None
                    digit = next(digits)
                    while digit != ']':
                        if digit == '-':
                            digit = next(digits)
                            for o in range(ord(p_digit), ord(digit) + 1):
                                dset.add(chr(o))
                        else:
                            dset.add(digit)
                            p_digit = digit
                        digit = next(digits)
                    # while
                    result.append(dset)
                else:
                    result.append({digit})
                # if
            # for
            return result

        def set_list_to_str(dset_list: List[Set[str]]) -> str:
            result = ''
            for dset in dset_list:
                if not dset:
                    continue
                if len(dset) == 1:
                    append = next(iter(dset))
                    if not append:
                        continue
                else:
                    append = ''.join(sorted(dset))
                    if append == '0123456789':
                        append = 'X'
                    else:
                        append = f'[{append}]'
                result = f'{result}{append}'
            return result

        new_digits = str_to_set_list(digits)
        if self.use_originators_calling_search_space:
            new_css = css
        else:
            new_css = ':'.join(self.css)
        if self.discard_digits:
            new_digits = discard_digits(new_digits)
        if self.called_party_prefix_digits:
            new_digits = [{d} for d in self.called_party_prefix_digits] + new_digits
        if self.route_next_hop_by_calling_party_number:
            raise NotImplementedError

        if self.called_party_mask:
            masked = list(d if m == 'X' else {m}
                          for m, d in zip_longest(self.called_party_mask[::-1],
                                                  new_digits[::-1],
                                                  fillvalue=''))
            new_digits = masked[::-1]
        new_digits = set_list_to_str(new_digits)
        log.debug(f'{self} translate {digits}->{new_digits}')
        return new_digits, new_css


class DnPattern(Pattern):
    def __init__(self, pattern: str, partition: str = ''):
        super(DnPattern, self).__init__(pattern=pattern, partition=partition, type=PatternType.DN)


class RoutePattern(Pattern):
    def __init__(self, pattern: str, partition: str = ''):
        super(RoutePattern, self).__init__(pattern=pattern, partition=partition, type=PatternType.RP)
