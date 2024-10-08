#!/usr/bin/env python
"""
Read enduser.csv from tar file and get TYPE_USER_ASSOCIATION values
"""
import csv
import glob
import os
from io import TextIOWrapper
from itertools import chain
from tarfile import TarFile

from dotenv import load_dotenv

from transform_tar import progress


def type_user_association_values(tar_file: str, csv_file: str) -> set[str]:
    with TarFile(name=tar_file, mode='r') as tar:
        try:
            file = TextIOWrapper(tar.extractfile(member=csv_file), encoding='utf-8')
        except KeyError:
            print(f'No "{csv_file}" in "{tar_file}"')
            return set()
        reader = csv.reader(file, delimiter=',', doublequote=True, escapechar=None, quotechar='"',
                            skipinitialspace=True, strict=True)
        first_line = next(reader)
        type_user_association_columns = [i
                                         for i, column in enumerate(first_line, start=0)
                                         if column.startswith('TYPE USER ASSOCIATION')]
        return set(chain.from_iterable((v
                                        for c in type_user_association_columns
                                        if (v := row[c]))
                                       for row in progress(reader)))


def main():
    load_dotenv()
    tar_file = os.getenv('TAR_FILE')
    if not tar_file or not os.path.isfile(tar_file):
        raise ValueError(f'{tar_file} is not a file')
    csv_file = 'enduser.csv'
    values = type_user_association_values(tar_file=tar_file, csv_file=csv_file)
    for v in sorted(values):
        print(f'* {v}')


def print_all():
    all_values = set()
    for tar in sorted(glob.glob('*.tar')):
        print(f'## {tar}')
        values = type_user_association_values(tar_file=tar, csv_file='enduser.csv')
        print()
        for v in sorted(values):
            print(f'* {v}')
        print()
        all_values.update(values)

    print('## All values')
    for v in sorted(all_values):
        print(f'* {v}')


if __name__ == '__main__':
    print_all()
    # main()
