from .base import Pattern, PatternType, ALL_PATTERN_TYPES, DnPattern, TranslationPattern, RoutePattern

from typing import Dict, Optional, Iterator, List, Set, Generator, Deque, Iterable, Tuple, Any, Callable, Union
from itertools import takewhile, tee, chain
from collections import defaultdict, deque
import re
from logging import getLogger
from ucmexport import Proxy
from time import perf_counter

__all__ = ['DaNode']

log = getLogger(__name__)
traversal_log = getLogger(f'{__name__}.traversal')
match_log = getLogger(f'{__name__}.match')

MAX_TRANSLATION_DEPTH = 5


class DaNode:
    """
    Da node represents a digit in the tree
    """
    __slots__ = ['childs', 'terminal_pattern', 'depth', 'representation', 'partitions', 'pattern_types', 'parent',
                 'full_representation', 'matching_digits']

    SINGLE_DIGIT_RE = re.compile(r'\[((?:\d|(?:\d-\d))+)]')

    ALL_DIGITS = set('*0123456789')

    def __init__(self, representation: str = '',
                 matching_digits: int = 1,
                 parent: 'DaNode' = None):
        """
        :param representation: representation for this node. Can be a wildcard ("X", "[1-5]", ...)
        :param parent: parent node
        """
        self.childs: Dict[str, List['DaNode']] = defaultdict(list)
        self.representation = representation
        self.parent = parent
        if parent is None:
            self.depth = 0
            self.full_representation = ''
        else:
            self.depth = parent.depth + 1
            self.full_representation = f'{parent.full_representation}{self.representation}'
        self.terminal_pattern: Dict[str, Pattern] = {}
        self.partitions: Set[str] = set()
        self.pattern_types: Set[PatternType] = set()
        self.matching_digits = matching_digits

    @staticmethod
    def from_proxy(proxy: Proxy, first_line_only=False) -> 'DaNode':
        """
        Get a DA tree based on TPs, RPs and DNs
        :param proxy:
        :param first_line_only:
        :return:
        """
        da_tree = DaNode()

        def tp_from_proxy_and_translation_pattern(proxy: Proxy,
                                                  translation_pattern: TranslationPattern) -> \
                TranslationPattern:
            return TranslationPattern(pattern=translation_pattern.pattern,
                                      partition=translation_pattern.partition,
                                      block=translation_pattern.block,
                                      css=proxy.css.partition_names(css_name=translation_pattern.css),
                                      urgent=translation_pattern.urgent,
                                      use_originators_calling_search_space=translation_pattern.use_originators_calling_search_space,
                                      discard_digits=translation_pattern.discard_digits,
                                      called_party_mask=translation_pattern.called_party_mask,
                                      called_party_prefix_digits=translation_pattern.called_party_prefix_digits,
                                      route_next_hop_by_calling_party_number=translation_pattern
                                      .route_next_hop_by_calling_party_number)

        # add all translation patterns to DA tree
        tps = proxy.translation_pattern.list
        start = perf_counter()
        for tp in tps:
            da_tree.add_pattern(tp_from_proxy_and_translation_pattern(proxy=proxy, translation_pattern=tp))
        log.debug(f'adding {len(tps)} translation patterns: {(perf_counter() - start) * 1000:.2f}ms')

        if first_line_only:
            # dnps of all 1st lines
            dnps = set(first_line.dn_and_partition
                       for phone in proxy.phones.list
                       if (first_line := next(iter(phone.lines.values()), None)))
        else:
            # All dnps of all lines
            dnps = set(chain.from_iterable((line.dn_and_partition
                                            for line in phone.lines.values())
                                           for phone in proxy.phones.list))
        start = perf_counter()
        for dnp in dnps:
            dn, partition = dnp.split(':')
            da_tree.add_pattern(DnPattern(pattern=dn, partition=partition))
        log.debug(f'adding {len(dnps)} DNs: {(perf_counter() - start) * 1000:.2f}ms')

        # finally all route patterns
        rps = proxy.route_pattern.list
        start = perf_counter()
        for rp in rps:
            da_tree.add_pattern(RoutePattern(pattern=rp.pattern, partition=rp.partition))
        log.debug(f'adding {len(rps)} Route Patterns: {(perf_counter() - start) * 1000:.2f}ms')

        return da_tree

    @property
    def all_child_nodes(self) -> Set['DaNode']:
        return set(chain.from_iterable(childs
                                       for childs in self.childs.values()))

    def add_pattern(self, pattern: Pattern) -> None:
        """
        Add a pattern to the DA tree starting at this node
        :param pattern: pattern to be added
        """
        self.add_digits(digits=iter(pattern.pattern), pattern=pattern)

    def repr_and_matching_set(self, digit: str, digits: Iterator[str]) -> Tuple[str, Set[str]]:
        # determine representation for new node
        # for something like "[1-9]" we need to collect everything until the closing bracket
        representation = digit
        if not digit:
            return '', set()
        if digit == '[':
            digits_matched = set()
            inner = takewhile(lambda x: x != ']', digits)
            for c in inner:
                if c == '-':
                    representation = f'{representation}{c}'
                    # noinspection PyUnboundLocalVariable
                    # digit after "-"
                    c = next(inner)
                    # noinspection PyUnboundLocalVariable
                    if c < previous_c:
                        raise ValueError
                    for i in range(int(previous_c), int(c)):
                        digits_matched.add(f'{i + 1}')
                else:
                    digits_matched.add(c)
                    # store previous digit in case the next "digit" is a "-"
                    previous_c = c
                # if
            # for
            # normalized representation without "-"
            representation = f'[{"".join(sorted(digits_matched))}]'
        elif digit in self.ALL_DIGITS:
            digits_matched = {digit}
        elif digit in '!X@':
            digits_matched = self.ALL_DIGITS
        elif digit == '+':
            if self.depth != 0:
                raise ValueError
            digits_matched = {'+'}
        else:
            raise ValueError
        return representation, digits_matched

    def add_digits(self, digits: Iterator[str], pattern: Pattern) -> None:
        """
        Add digit string as child of node
        :param pattern: pattern to be added at the terminating node
        :param digits: iterator over the digits of the digit string to be added
        :raises ValueError: illegal digit string
        """
        self.partitions.add(pattern.partition)
        self.pattern_types.add(pattern.type)
        # skip over separator
        while (first_digit := next(digits, None)) and first_digit in '.#\\':
            if first_digit == '\\' and self.depth != 0:
                raise ValueError
        if first_digit is None:
            # Reached the end og the digit string
            # put the terminal pattern into this node
            # same pattern can exist in multiple partitions and we want to keep track of all terminal
            # patterns
            self.terminal_pattern[pattern.partition] = pattern
            return
        representation, digits_matched = self.repr_and_matching_set(digit=first_digit, digits=digits)
        # we need a child node for every digit matched
        # a new child node is not needed for a given matched digit if one of the existing child nodes for that digit
        # has the same representation
        # we might be forced to climb down multiple trees...
        new_node = None
        add_to_nodes: Set[DaNode] = set()
        for digit_matched in digits_matched:
            child_nodes_for_digit_matched = self.childs[digit_matched]
            child_node_with_matching_representation = next((child
                                                            for child in child_nodes_for_digit_matched
                                                            if child.representation == representation),
                                                           None)
            if child_node_with_matching_representation:
                # need to climb down that node
                add_to_nodes.add(child_node_with_matching_representation)
            else:
                # new node needs to be added with the new representation
                new_node = new_node or DaNode(representation=representation,
                                              parent=self,
                                              matching_digits=len(digits_matched))
                self.childs[digit_matched].append(new_node)
        # now continue to climb down all nodes
        if new_node:
            add_to_nodes.add(new_node)
        if len(add_to_nodes) == 1:
            digit_iters = [digits]
        else:
            digit_iters = tee(digits, len(add_to_nodes))
        for child_node, digit_iter in zip(add_to_nodes, digit_iters):
            child_node.add_digits(digits=digit_iter, pattern=pattern)

    def terminal_nodes(self) -> Generator['DaNode', None, None]:
        """
        Traverse through the tree breadth 1st and yield all nodes with terminal patterns
        """
        for node in self.breadth_first_traversal():
            if node.terminal_pattern:
                yield node
            # for
        # while

    def terminal_patterns(self) -> Generator[Pattern, None, None]:
        for node in self.terminal_nodes():
            for tp in node.terminal_pattern:
                yield tp

    def find_leaves(self, depth: int, partitions: List[str] = None, partition_set: Set[str] = None,
                    pattern_types: Set[PatternType] = None,
                    stop_decent: Set[PatternType] = None) -> Generator[Tuple['DaNode', str], None, None]:
        partitions = partitions or list(self.partitions)
        partition_set = partition_set or set(partitions)
        pattern_types = pattern_types or ALL_PATTERN_TYPES
        stop_decent = stop_decent or {PatternType.DN}
        traversal_log.debug(
            f'find_leaves: depth {depth} partitions {":".join(partition_set)} pattern_types: '
            f'{", ".join(str(pt) for pt in pattern_types)} stop_decent: {", ".join(str(s) for s in stop_decent)}')

        def dial_string_context(node: DaNode, dial_string: str) -> str:
            return f'{dial_string}{node.representation}'

        traversal = self.breadth_first_traversal_with_context(start_context='', context_func=dial_string_context)

        def next_node(dial_string: str = '', descend: List[DaNode] = None) -> Tuple[Optional[DaNode], str]:
            descend = descend or []
            try:
                node = traversal.send((n, dial_string_context(node=n, dial_string=dial_string))
                                      for n in descend)
            except StopIteration:
                node = (None, '')
            return node

        node, dial_string = next(traversal)
        while node:
            traversal_log.debug(f'find_leaves: depth {node.depth} representation {node.full_representation} '
                                f'pattern types {", ".join(f"{pt}" for pt in node.pattern_types)} '
                                f'partitions: {", ".join(node.partitions)}')
            if not pattern_types & node.pattern_types:
                # There are no pattern types on the current nodes common with the nodes we are interested in
                # no need to look at this
                traversal_log.debug(f'find_leaves: depth {node.depth} representation {node.full_representation} '
                                    f'pattern types {", ".join(f"{pt}" for pt in node.pattern_types)} '
                                    f'partitions: {", ".join(node.partitions)} -> ignore, stop descend, no matching '
                                    f'pattern '
                                    f'types')
                node, dial_string = next_node()
                continue

            if not partition_set & node.partitions:
                # no common partitions: can skip this node
                traversal_log.debug(f'find_leaves: depth {node.depth} representation {node.full_representation} '
                                    f'pattern types {", ".join(f"{pt}" for pt in node.pattern_types)} '
                                    f'partitions: {", ".join(node.partitions)} -> ignore, stop descend, '
                                    f'no common partitions')
                node, dial_string = next_node()
                continue

            if node.terminal_pattern:
                traversal_log.debug(f'find_leaves: terminal pattern: {node.terminal_pattern}')

            # yield if we reached the max. depth or if we have a terminal pattern
            # also yield if the pattern types below this node are identified by stop_decent
            if node.depth == depth or \
                    node.terminal_pattern or \
                    node.pattern_types == stop_decent:
                traversal_log.debug(f'find_leaves: depth {node.depth} representation {node.full_representation} '
                                    f'pattern types {", ".join(f"{pt}" for pt in node.pattern_types)} '
                                    f'partitions: {", ".join(node.partitions)} -> yield')
                yield node, dial_string
            # no deed to climb further down if we reached the maximum depth or the subtree only has patterns
            # included in the stop decent set
            if node.depth == depth or node.pattern_types == stop_decent:
                # no need to climb further down
                traversal_log.debug(f'find_leaves: depth {node.depth} representation {node.full_representation} '
                                    f'pattern types {", ".join(f"{pt}" for pt in node.pattern_types)} '
                                    f'partitions: {", ".join(node.partitions)} -> stop descend')
                node, dial_string = next_node()
                continue
            # Determine childs to climb down into: only childs with partition match
            climb_down = [child
                          for child in node.all_child_nodes
                          if child.partitions & partition_set]
            node, dial_string = next_node(dial_string=dial_string, descend=climb_down)
        return

    def breadth_first_traversal_with_context(self, start_context: Any,
                                             context_func: Callable[['DaNode', Any], Any] = None) -> \
            Generator[Tuple['DaNode', Any], Optional[Iterable[Tuple['DaNode', Any]]], None]:
        node_queue: Deque[Tuple['DaNode', Any]] = deque()
        node_queue.append((self, start_context))
        while node_queue:
            node, context = node_queue.popleft()
            traversal_log.debug(f'breadth_first_traversal: yield {node.depth}:{node.full_representation}')
            descend = yield node, context

            if descend is None:
                # descend into all child nodes
                if context_func:
                    node_queue.extend((n, context_func(n, context)) for n in node.all_child_nodes)
                else:
                    node_queue.extend((n, context) for n in node.all_child_nodes)
            else:
                node_queue.extend(descend)

    def breadth_first_traversal(self) -> Generator['DaNode', Optional[Iterable['DaNode']], None]:
        """
        Traverse the tree breadth 1st
        :return: Nodes of the tree in breadth 1st order
        """
        for node, _ in self.breadth_first_traversal_with_context(None):
            yield node

    def matching_nodes(self, digits: Union[str, Iterator[str]],
                       css: Union[str, Set[str]],
                       parent_digits: str = None,
                       parent_alternatives: int = 1) -> Generator[Tuple['DaNode', int], None, None]:
        """
        Yield matching DA nodes for given digits and CSS
        :param digits: digit string to match
        :param css: CSS string
        :param parent_digits:
        :param parent_alternatives:
        :return: Tuple of da node and match priority (the lower the better)
        """
        if isinstance(digits, str):
            digits = iter(digits)
        if isinstance(css, str):
            css = set(css.split(':'))
        parent_digits = parent_digits or ''
        digit = next(digits, '')
        digit_repr, digit_set = self.repr_and_matching_set(digit=digit, digits=digits)
        match_log.debug(f'{self} digits {parent_digits}:{digit_repr}')
        parent_digits = f'{parent_digits}{digit_repr}'
        parent_alternatives = parent_alternatives * self.matching_digits
        if digit == '':
            # last digit consumed
            if self.terminal_pattern:
                match_log.debug(f'matches({parent_digits}): reached end of digits: yield {self}')
                yield self, parent_alternatives
            else:
                match_log.debug(f'matches({parent_digits}): reached end of digits: no terminal pattern {self}')
            return
        if self.representation == '!':
            # match arbitrary digits -> consume further digits on this node w/o climbing down
            yield from self.matching_nodes(digits=digits, css=css, parent_digits=parent_digits,
                                           parent_alternatives=parent_alternatives)
            return
        matching_childs = set(chain.from_iterable(self.childs.get(d, []) for d in digit_set))
        # matching_childs = self.childs.get(digit, [])
        # filter by CSS
        matching_childs = [mc
                           for mc in matching_childs
                           if css & mc.partitions]
        if not matching_childs:
            match_log.debug(f'{self} no match on {digit_repr}')
            return

        match_log.debug(f'{len(matching_childs)} matching childs: {", ".join(f"{mc}" for mc in matching_childs)}')
        if len(matching_childs) == 1:
            yield from next(iter(matching_childs)).matching_nodes(digits=digits, css=css, parent_digits=parent_digits,
                                                                  parent_alternatives=parent_alternatives)
        else:
            for digits, child in zip(tee(digits, len(matching_childs)), matching_childs):
                yield from child.matching_nodes(digits=digits, css=css, parent_digits=parent_digits,
                                                parent_alternatives=parent_alternatives)
            # for
        # if

    def lookup(self, digits: str, css: str, tp_depth=0) -> List[Pattern]:
        """
        DA Lookup and return matched Pattern
        :param digits: digit string to consume
        :param css: string representation of the css; colon separated list of partition names
        :param tp_depth: translation recursion depth
        :return: pattern found as result of DA lookup
        """
        if isinstance(css, str):
            css_set = set(css.split(':'))
        else:
            css_set = set(css)
        matches = list(self.matching_nodes(digits=digits, css=css))
        if not matches:
            return []
        best_match_quality = min(m[1] for m in matches)
        best_matches = [match[0]
                        for match in matches
                        if match[1] == best_match_quality]
        # sorting by match priority makes sure that the best pattern(s) are at the start
        matches.sort(key=lambda x: x[1])
        # best_match = matches[0][0]
        # get all terminal patterns associated with these best matching nodes where the partition is part of the CSS
        terminal_patterns = defaultdict(list)
        for best_match in best_matches:
            for partition, pattern in best_match.terminal_pattern.items():
                if partition in css_set:
                    terminal_patterns[partition].append(pattern)
        if len(terminal_patterns) == 1:
            patterns = next(iter(terminal_patterns.values()))
        else:
            # we have multiple patterns with the same matching quality in various partitions
            # in that case the partition order in the CSS has to be used as a tie_breaker
            # iterate through all partitions until terminal_patterns has an entry in that partition
            patterns = next(patterns
                            for partition in css.split(':')
                            if (patterns := terminal_patterns.get(partition)) is not None)
        # pattern is now a list of patterns that match
        patterns_after_translation = []
        for pattern in patterns:
            if isinstance(pattern, TranslationPattern):
                if tp_depth == MAX_TRANSLATION_DEPTH:
                    continue
                # translate and try again
                pattern: TranslationPattern
                digits, css = pattern.translate(digits, css)
                if lookup_after_translation := self.lookup(digits, css, tp_depth=tp_depth + 1):
                    patterns_after_translation.extend(lookup_after_translation)
            else:
                patterns_after_translation.append(pattern)
        return patterns_after_translation

    def __str__(self):
        return f'{self.depth}:{self.full_representation}'

    def __repr__(self):
        return f'{self.__class__.__name__}({self})'

    def pretty_lines(self, parent_representation: str = '') -> Generator[str, None, None]:
        indent = ' ' * (self.depth * 2)
        yield f'{indent}partitions: {", ".join(p or "NONE" for p in sorted(self.partitions))}'
        yield f'{indent}pattern types: {", ".join(sorted(f"{pt}" for pt in self.pattern_types))}'
        if self.terminal_pattern:
            if len(self.terminal_pattern) > 1:
                for partition in sorted(self.terminal_pattern):
                    pattern = self.terminal_pattern[partition]
                    partition = partition or 'NONE'
                    yield f'{indent}{self.depth}:{parent_representation}{self.representation}' \
                          f': terminal: {pattern}'
                pass
            else:
                pattern = next(iter(self.terminal_pattern.values()))
                yield f'{indent}{self.depth}:{parent_representation}{self.representation}' \
                      f' terminal: {pattern}'
        child_nodes = self.all_child_nodes
        for child_node in child_nodes:
            digits = sorted(digit
                            for digit, childs in self.childs.items()
                            if child_node in childs)
            full_representation = f'{parent_representation}{self.representation}'
            if len(digits) == 1:
                matching = f'{digits[0]}'
            else:
                if self.ALL_DIGITS - set(digits):
                    matching = f'[{"".join(digits)}]'
                else:
                    matching = 'X'
            matching = f'{full_representation}{matching}'
            yield f'{indent}{self.depth}:{full_representation}' \
                  f' matching: {matching}'
            yield from child_node.pretty_lines(parent_representation=f'{parent_representation}{self.representation}')

    def pretty(self) -> str:
        return "\n".join(self.pretty_lines())
