#!/usr/bin/env python
"""
Transform a UCM config export TAR file by applying transformations to the CSV files within it
"""
import csv
import io
import os
import tarfile
import time
from collections.abc import Callable
from io import TextIOWrapper, TextIOBase
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


def enduser_filter_deleted_time_stamp(in_file: TextIOBase) -> TextIOBase:
    reader = csv.DictReader(in_file, delimiter=',', doublequote=True, escapechar=None, quotechar='"',
                            skipinitialspace=True, strict=True)
    out_file = io.StringIO()
    writer = csv.DictWriter(out_file, fieldnames=reader.fieldnames, delimiter=',', doublequote=True,
                            escapechar=None, quotechar='"', quoting=csv.QUOTE_MINIMAL, skipinitialspace=True,
                            strict=True)
    writer.writeheader()
    for row in progress(reader):
        if row['DELETED TIME STAMP'] == 'NULL':
            writer.writerow(row)
    out_file.seek(0)
    return out_file


def enduser_delete_cols_121_43316(in_file: TextIOBase) -> TextIOBase:
    csv_reader = csv.reader(in_file, delimiter=',', doublequote=True, escapechar=None, quotechar='"',
                            skipinitialspace=True, strict=True)

    out_file = io.StringIO()
    csv_writer = csv.writer(out_file, delimiter=',', doublequote=True,
                            escapechar=None, quotechar='"', quoting=csv.QUOTE_MINIMAL, skipinitialspace=True,
                            strict=True)

    for row in progress(csv_reader):
        row = row[:121] + row[43317:]
        csv_writer.writerow(row)
    out_file.seek(0)
    return out_file


csv_transforms: dict[str, list[Callable[[TextIOBase], TextIOBase]]] = {
    'enduser.csv': [enduser_delete_cols_121_43316,
                    enduser_filter_deleted_time_stamp]}


def transform():
    # open the TAR file
    load_dotenv()
    input_tar = os.getenv('TAR_FILE')
    if not input_tar or not os.path.isfile(input_tar):
        raise ValueError(f'{input_tar} is not a file')
    with TarFile(name=input_tar, mode='r') as tar:
        out_tar = f'{os.path.splitext(input_tar)[0]}_transformed.tar'
        with TarFile(name=out_tar, mode='w') as out:
            # iterate over the members of the TAR file
            for member in tar.getmembers():
                member: tarfile.TarInfo
                # check if the member is a CSV file
                if member.name.endswith('.csv') and (transformers := csv_transforms.get(member.name)):
                    print(f'transforming {member.name}', flush=True)
                    file = TextIOWrapper(tar.extractfile(member=member.name), encoding='utf-8')
                    for transform in transformers:
                        transformed = transform(file)
                        file.close()
                        file = transformed
                    bytes_io = io.BytesIO(file.read().encode('utf-8'))
                    file.close()
                    ti = tarfile.TarInfo(name=member.name)
                    ti.size = len(bytes_io.getvalue())
                    # set mtime to current time
                    ti.mtime = int(time.time())
                    bytes_io.seek(0)
                    out.addfile(tarinfo=ti, fileobj=bytes_io)
                    bytes_io.close()
                else:
                    # not a CSV file or no transformer
                    # copy as is
                    print(f'copying {member.name} as is', flush=True)
                    file = tar.extractfile(member)
                    out.addfile(member, file)
                    file.close()
                # if
            # for
        # with
    # with
    return


if __name__ == '__main__':
    transform()
