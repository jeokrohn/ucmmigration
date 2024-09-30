#!/usr/bin/env python
"""
Analyse a UCM config export TAR file: look at enduser.csv and identify columns only used by very few users as
candidates for elimination
"""
import logging
import os
import re
from collections import defaultdict
from collections.abc import Iterable
from csv import DictReader
from functools import reduce
from io import TextIOWrapper
from itertools import chain
from tarfile import TarFile

from dotenv import load_dotenv


def progress(items):
    print(f'reading ', end='', flush=True)
    i = 0
    for i, e in enumerate(items):
        if i % 200 == 0:
            print('.', end='', flush=True)
        yield e
    print(f', got {i + 1} records')


def column_repr(columns: Iterable[str]) -> str:
    # group columm names that are something like 'fooo nnnnn'
    col_name_re = re.compile(r'^(.+) (\d+)$')
    columns_by_prefix: dict[str, list[str]] = defaultdict(list)
    r = list()
    for column_name in columns:
        match = col_name_re.match(column_name)
        if match:
            columns_by_prefix[match.group(1)].append(match.group(2))
        else:
            columns_by_prefix[column_name].append(column_name)
    for column_name in sorted(columns_by_prefix):
        suffixes = columns_by_prefix[column_name]
        if len(suffixes) == 1:
            try:
                r.append(f'{column_name} {int(suffixes[0])}')
            except ValueError:
                r.append(column_name)
            continue
        suffixes: list[int] = sorted(map(int, suffixes))
        start_suffix = None
        column_entry = f'{column_name}'
        for suffix in suffixes:
            if start_suffix is None:
                start_suffix = suffix
            elif suffix != prev_suffix + 1:
                column_entry = f'{column_entry} {start_suffix}-{suffix}'
                start_suffix = None
            prev_suffix = suffix
        # for
        if start_suffix is not None:
            column_entry = f'{column_entry} {start_suffix}'
            if suffix != start_suffix:
                column_entry = f'{column_entry}-{suffix}'
        r.append(column_entry)
    # for
    return ', '.join(r)


def evaluate():
    load_dotenv()
    tar_file = os.getenv('TAR_FILE')
    if not tar_file or not os.path.isfile(tar_file):
        raise ValueError(f'{tar_file} is not a file')

    csv_file = 'enduser.csv'
    with TarFile(name=tar_file, mode='r') as tar:
        file = TextIOWrapper(tar.extractfile(member=csv_file), encoding='utf-8')

        def upper_first_line(it):
            first_line = next(it)
            first_line_upper = first_line.upper()
            if first_line != first_line_upper:
                logging.warning(f'found lowercase header in {csv_file}')
            return chain([first_line_upper], it)

        file = upper_first_line(file)
        csv_reader = DictReader(file, delimiter=',', doublequote=True, escapechar=None, quotechar='"',
                                skipinitialspace=True, strict=True)
        # try to identify empty columns
        col_usage: dict[str, set[str]] = defaultdict(set)
        key_field = 'USER ID'
        for row_number, row in enumerate(progress(csv_reader)):
            key = row[key_field]
            for col in (col for col, value in row.items() if value):
                col_usage[col].add(key)
        print(f'Read {row_number + 1} records from {csv_file}')
        print(f'{len(csv_reader.fieldnames)} columns in {csv_file}')
        # group columns be number of users using them
        col_by_usage: dict[int:list[str]] = reduce(lambda r, e: r[len(e[1])].append(e[0]) or r,
                                                   col_usage.items(),
                                                   defaultdict(list))
        col_by_usage: list[tuple[int, list[str]]] = sorted(col_by_usage.items(), key=lambda x: x[0])
        for usage, columns in col_by_usage:
            if usage > 10:
                break
            print(f'{len(columns)} columns with {usage} users')
            users = sorted(set(chain.from_iterable(col_usage[col] for col in columns)))
            print(f' users: {", ".join(users)}')
            user_len = max(len(user) for user in users)
            for user in users:
                user_columns = set(col
                                   for col in columns
                                   if user in col_usage[col])
                print(f'  {user:{user_len}}: {column_repr(user_columns)}')
                # determine the column indices for the columns
                col_indices = set()
                for i, column_name in enumerate(csv_reader.fieldnames):
                    if column_name in user_columns:
                        col_indices.add(i)
                print(f'  {" ":{user_len}} min field index: {min(col_indices)}, max field index: {max(col_indices)}')
            # for
        # for

if __name__ == '__main__':
    evaluate()
