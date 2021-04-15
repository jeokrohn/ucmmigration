from tarfile import TarFile
from io import TextIOWrapper
from csv import DictReader
from re import compile
from itertools import chain

import logging

from collections import defaultdict
from typing import List, Dict, Set

__all__ = ['RE_TO_SNAIL', 'to_snail', 'ObjBase', 'CsvBase', 'DNAandPartitionRelated', 'REMOVE_ATTR_FROM_PARENT']

log = logging.getLogger(__name__)

RE_TO_SNAIL = compile(r"[ ./\-()']")

# remove attributes from dict of parent: has significant performance impact
# .. and does not really save memory
REMOVE_ATTR_FROM_PARENT = False


def to_snail(key: str) -> str:
    """
    Convert a header ro snail case. For example: "JIM DOE" -> "jim_doe"
    :param key: string to convert
    :return: snail case version
    """
    return RE_TO_SNAIL.sub('_', key).lower().strip('_')


CHECK_FOR_NONE = False      # Raise an Exception if some CSV has a "None" column
POP_NONE = True             # Remove "None" column when importing CSV
CSV_TO_UPPER = True         # Convert all CSV Headers to uppercase
WARN_LOWERCASE_HEADER = True   # log a warning for CSV files that have lowercase headers

DNAandPartitionRelated = Dict[str, Set[str]]


class ObjMeta(type):

    def __new__(mcs, class_name, *args, **kwargs):
        c = super(ObjMeta, mcs).__new__(mcs, class_name, *args, **kwargs)
        # class specific mapping from snail case identifiers to attributes
        c._snail_to_attribute = dict()
        return c


class ObjBase(metaclass=ObjMeta):
    __slots__ = ['_obj']

    def __init__(self, o: Dict):
        if CHECK_FOR_NONE:
            assert next((k for k in o if k is None), '') == '', \
                f'ObjBase.__init__ None key found {", ".join(f"{k}:{v}" for k, v in o.items())}'
        if POP_NONE:
            # sometimes there seems to be a "None" column at the end which breaks stuff
            o.pop(None, None)
        self._obj = o

    @property
    def dict(self):
        return self._obj

    def __getattr__(self, item):
        if item == '_obj':
            raise AttributeError
        attribute = self._snail_to_attribute.get(item)
        if attribute is None:
            # check if there is any attribute that matches the snail..
            attribute = next((a for a in self._obj if item == to_snail(a)), None)
            if attribute is None:
                raise AttributeError
            self._snail_to_attribute[item] = attribute
        try:
            r = self._obj[attribute]
        except KeyError:
            raise AttributeError

        if r == 't':
            return True
        elif r == 'f':
            return False
        return r

    def __repr__(self):
        return f'{self.__class__.__name__}({self})'

    def __str__(self):
        return super(ObjBase, self).__repr__()


class CsvBase:
    __slots__ = ['_tar', '_objects', '_by_attribute']

    def __init__(self, tar: str):
        self._tar = tar
        self._objects = None
        self._by_attribute: Dict[str, Dict[str, List[...]]] = dict()

    @property
    def list(self) -> List[ObjBase]:
        if self._objects is None:
            # read from CSV. Determine CSV file name from class name
            # class names are assumed to be <csv file name>Container
            csv_file = self.__class__.__name__.lower()
            assert csv_file.endswith('container')
            # strip 'container'
            csv_file = f'{csv_file[:-9]}.csv'
            log.debug(f'{self.__class__.__name__}.list: reading {csv_file} from {self._tar}')

            with TarFile(name=self._tar, mode='r') as tar:
                try:
                    file = TextIOWrapper(tar.extractfile(member=csv_file), encoding='utf-8')
                except KeyError:
                    # file not found
                    self._objects = []
                else:
                    if CSV_TO_UPPER:
                        def upper_first_line(it):
                            first_line = next(it)
                            first_line_upper = first_line.upper()
                            if WARN_LOWERCASE_HEADER and first_line != first_line_upper:
                                logging.warning(f'found lowercase header in {csv_file}')
                            return chain([first_line_upper], it)
                        file = upper_first_line(file)
                    csv_reader = DictReader(file, delimiter=',', doublequote=True, escapechar=None, quotechar='"',
                                            skipinitialspace=True, strict=True)
                    self._objects = [self.__class__.factory(o) for o in csv_reader]
            log.debug(f'done reading {csv_file} from {self._tar}: {len(self._objects)} objects read')
        return self._objects

    def by_attribute(self, attribute: str) -> Dict[str, List[ObjBase]]:
        """
        get list of objects by attribute key
        :param attribute: attribute or property name to create the grouping from
        :return: dictionary with attribute values as key and list of objects as values
        """

        def attr_key(o: ObjBase) -> str:
            """
            get key value by accessing an attribute of an object; but respect snail mapping
            :param o: object
            :return: key value
            """
            return o.__getattr__(attribute)

        def property_key(o: ObjBase) -> str:
            """
            get key value by evaluating a property
            :param o: object
            :return: key value
            """
            return prop.fget(o)

        # _by_attribute is a cache of groupings
        if (d := self._by_attribute.get(attribute)) is None:
            # 1st time this grouping is requested
            # attribute can be a name of a property or an attribute
            if prop := self.factory.__dict__.get(attribute):
                # get keys using fget() of the property object
                key = property_key
            else:
                # get keys by directly accessing the attribute: look at the dict of an object
                key = attr_key
            d = defaultdict(list)
            for o in self.list:
                d[key(o)].append(o)
            d = dict(d)
            self._by_attribute[attribute] = d
        return d

    def __getattr__(self, item: str):
        """
        Implement properties in the form of by_<attribute>.
        Each function returns a dict of list of objects where the key are the attribute values
        :param item:
        :return:
        """
        if not item.startswith('by_'):
            raise AttributeError
        attribute = item[3:]
        try:
            return self.by_attribute(attribute)
        except KeyError:
            raise AttributeError

    def get(self, item, default=None):
        try:
            return self[item]
        except KeyError:
            return default
