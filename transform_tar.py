#!/usr/bin/env python
"""
Transform a UCM config export TAR file by applying transformations to the CSV files within it
"""
import csv
import io
import os
import re
import tarfile
import time
from argparse import ArgumentParser
from collections.abc import Callable
from contextlib import contextmanager
from functools import partial
from io import TextIOWrapper, TextIOBase
from tarfile import TarFile
from typing import Optional

# columns to remove from phones.csv
PHONE_CSV_EXCLUDED_FIELDS = ['Services Provisioning', 'CSS', 'AAR CSS', 'Network Locale', 'Media Resource Group List',
                             'User Hold MOH Audio Source', 'Network Hold MOH Audio Source', 'Device User Locale',
                             'Packet Capture Mode', 'Packet Capture Duration', 'Built in Bridge', 'Privacy',
                             'Retry Video Call as Audio', 'Ignore Presentation Indicators', 'Module',
                             'Phone Load Name', 'Module # Load Name', 'Information', 'Directory', 'Messages',
                             'Services', 'Authentication Server', 'Proxy Server', 'Idle', 'Idle Timer',
                             'MLPP Indication', 'MLPP Preemption', 'MLPP Domain', 'MTP Required', 'Digest User',
                             'Allow CTI Control Flag', 'Device Presence Group', 'Device Security Profile',
                             'Device Subscribe CSS', 'Unattended Port', 'Require DTMF Reception', 'RFC2833 Disabled',
                             'Certificate Operation', 'Authentication String', 'Operation Completes By',
                             'Device Protocol', 'Secure Shell User', 'Secure Shell Password', 'XML', 'Dial Rules',
                             'CSS Reroute', 'Rerouting Calling Search Space', 'DTMF Signalling',
                             'Default DTMF Capability',
                             'MTP Preferred Originating Codec', 'Logout Profile', 'Signaling Port',
                             'Outgoing Caller ID Pattern',
                             'Calling Party Selection', 'Calling Party Presentation', 'Display IE Delivery',
                             'Redirecting Number IE Delivery Outbound', 'Redirecting Number IE Delivery Inbound',
                             'Gatekeeper Name', 'Technology Prefix', 'Zone', 'Motorola WSM Connection',
                             'Subscriber Cellular Number', 'Follow me only when caller has dialed cellular num',
                             'Disable Application Dial Rules', 'AAR Group', 'Logged Into Hunt Group', 'Remote Device',
                             'Device Mobility Mode', 'DND Option', 'DND Incoming Call Alert',
                             'BLF Audible Alert Setting (Phone Busy)',
                             'BLF Audible Alert Setting (Phone Idle)', 'Protected Device', 'Join Across Lines',
                             'Single Button Barge',
                             'Application User', 'Always Use Prime Line', 'Always Use Prime Line for Voice Message',
                             'Use Trusted Relay Point', 'Outbound Call Rollover', 'Phone Personalization',
                             'Primary Phone',
                             'Hotline Device', 'Secure Directory URL', 'Secure Idle URL',
                             'Secure Information URL', 'Secure Messages URL', 'Secure Services URL', 'SRTP Allowed',
                             'Feature Control Policy', 'Device Trust Mode', 'Allow presentation sharing using BFCP',
                             'Early Offer support for voice and video calls (insert MTP if needed)',
                             'Caller ID Calling Party Transformation CSS',
                             'Caller ID Use Device Pool Calling Party Transformation CSS',
                             'Remote Number Calling party Transformation CSS',
                             'Remote Number Use Device Pool Calling Party Transformation CSS',
                             'Allow iX Applicable Media', 'Require off-premise location', 'Confidential Access Mode',
                             'Confidential Access Level',
                             'Route calls to all remote destinations when client is not connected',
                             'Emergency Location (ELIN) Group', 'Third-party Registration Required',
                             'Block Incoming Calls while Roaming',
                             'Home Network ID', 'Mobility Identity Name', 'Mobility Identity Destination Number',
                             'Mobility Identity Answer Too Soon Timer', 'Mobility Identity Answer Too Late Timer',
                             'Mobility Identity Delay Before Ringing Cell', 'Mobility Identity Time Zone',
                             'Mobility Identity Is Mobile Phone',
                             'Mobility Identity Enable Mobile Connect', 'Mobility Identity Mobility Profile',
                             'Line CSS',
                             'AAR Group(Line)', 'Line User Hold MOH Audio Source', 'Line Network Hold MOH Audio Source',
                             'Auto Answer', 'Forward All CSS', 'Forward Busy Internal CSS', 'Forward Busy External CSS',
                             'Forward No Answer Internal CSS', 'Forward No Answer External CSS',
                             'Forward No Coverage Internal CSS',
                             'Forward No Coverage External CSS', 'MLPP Target', 'MLPP CSS',
                             'MLPP No Answer Ring Duration',
                             'Busy Trigger', 'Visual Message Waiting Indicator Policy', 'Ring setting (Phone Idle)',
                             'Ring Setting (Phone Active)', 'Caller Name', 'Caller Number', 'Redirected Number',
                             'Dialed Number', 'Line Description', 'Line Presence Group',
                             'Secondary CSS for Forward All',
                             'Forward on CTI Failure Voice Mail', 'Forward on CTI Failure Destination',
                             'Forward on CTI Failure CSS', 'AAR Destination Mask', 'AAR Voice Mail',
                             'Forward Unregistered Internal CSS',
                             'Forward Unregistered External CSS', 'Hold Reversion Ring Duration',
                             'Hold Reversion Notification Interval',
                             'Recording Profile', 'Monitoring Calling Search Space',
                             'Calling Search Space Activation Policy',
                             'CPG Audio Alert Setting(Phone Idle)', 'CPG Audio Alert Setting(Phone Active)',
                             'Park Monitor Forward No Retrieve Ext Destination',
                             'Park Monitor Forward No Retrieve Int Destination',
                             'Park Monitor Forward No Retrieve Int Voice Mail',
                             'Park Monitor Forward No Retrieve Ext Voice Mail',
                             'Park Monitor Forward No Retrieve Ext CSS', 'Park Monitoring Reversion Timer',
                             'Park Monitor Forward No Retrieve Int CSS',
                             'Party Entrance Tone', 'Log Missed Calls', 'Allow Control of Device from CTI',
                             'URI # on Directory Number',
                             'URI # Route Partition on Directory Number', 'URI # Is Primary on Directory Number',
                             'Reject Anonymous Calls', 'Urgent Priority', 'Recording Media Source',
                             'Enterprise Is Urgent',
                             'Enterprise Advertise via globally', 'Enterprise Add to Local Route Partition',
                             'Enterprise Route Partition',
                             'E.164 Is Urgent', 'E.164 Advertise via globally', 'E.164 Add to Local Route Partition',
                             'E.164 Route Partition', 'Line Confidential Access Mode', 'Line Confidential Access Level',
                             'External Call Control Profile',
                             'Call Control Agent Profile', 'IsEnterprise Advertised Failover Number',
                             'IsE.164 Advertised Failover Number',
                             'URI # Advertise Globally via ILS', 'Calling Line ID Presentation When Diverted',
                             'Intercom Maximum Number of Calls', 'Intercom Directory Number',
                             'Intercom Route Partition',
                             'Intercom Description', 'Intercom Alerting Name', 'Intercom ASCII Alerting Name',
                             'Intercom CSS', 'Intercom Presence Group',
                             'Intercom Display', 'Intercom ASCII Display', 'Intercom Line Text Label',
                             'Intercom Speed Dial',
                             'Intercom External Phone Number Mask', 'Intercom Caller Name', 'Intercom Caller Number',
                             'Intercom Auto Answer',
                             'Intercom Default Activated Device']

# columns to remove from enduser.csv
ENDUSER_CSV_EXCLUDED_FIELDS = ['ASSOCIATED PC', 'MIDDLE NAME', 'PAGER', 'HOME PHONE', 'BUILDING', 'SITE',
                               'UNIQUE IDENTIFIER',
                               'NICKNAME',
                               'DELETED TIME STAMP',
                               'DIGEST CREDENTIALS', 'PRESENCE GROUP',
                               'SUBSCRIBE CSS',
                               'ALLOW CONTROL OF DEVICE FROM CTI', 'MAX. DESK PICKUP WAIT TIME',
                               'REMOTE DESTINATION LIMIT',
                               'ENABLE USER FOR UNIFIED CM IM AND PRESENCE', 'ENABLE EMCC',
                               'INCLUDE MEETING INFORMATION IN PRESENCE', 'ASSIGNED PRESENCE SERVER',
                               'ENABLE END USER TO HOST CONFERENCE NOW', 'MEETING NUMBER', 'ATTENDEES ACCESS CODE',
                               'EM MAX LOGIN TIME', 'SELF-SERVICE USER ID', 'PASSWORD LOCKED BY ADMIN',
                               'PASSWORD CANT CHANGE', 'PASSWORD MUST CHANGE AT NEXT LOGIN',
                               'PASSWORD DOES NOT EXPIRE',
                               'PASSWORD AUTHENTICATION RULE', 'PASSWORD', 'PIN LOCKED BY ADMIN',
                               'PIN CANT CHANGE',
                               'PIN MUST CHANGE AT NEXT LOGIN', 'PIN DOES NOT EXPIRE', 'PIN AUTHENTICATION RULE',
                               'PIN', 'APPLICATION SERVER NAME', 'CONTENT', 'ACCESS CONTROL GROUP',
                               'DEFAULT PROFILE', 'DEVICE NAME', 'DESCRIPTION',
                               'TYPE USER ASSOCIATION',
                               'TYPE PATTERN USAGE',
                               'NAME DIALING', 'MLPP PRECEDENCE AUTHORIZATION LEVEL',
                               'MLPP USER IDENTIFICATION NUMBER',
                               'MLPP PASSWORD', 'HEADSET SERIAL NUMBER']


def progress(items):
    """
    Primitive progress indicator; print a "." every 200 records
    """
    i = 0
    for i, e in enumerate(items):
        if i % 200 == 0:
            print('.', end='', flush=True)
        yield e
    print(f', got {i + 1} records', end='', flush=True)


def remove_fields(in_file: TextIOBase, fields_to_remove: list[str], max_devices: int=None) -> TextIOBase:
    """
    Remove fields from a CSV file
    """

    def single_column(column: str) -> str:
        """
        Regular expression to match for a single column
        """
        r = f'(?:{column})'
        return r

    # buid regex to match columns to remove
    col_re = f'^({"|".join(single_column(col) for col in fields_to_remove)})( \d+)?$'
    col_re = re.compile(col_re)

    reader = csv.reader(in_file, delimiter=',', doublequote=True, escapechar=None, quotechar='"',
                        skipinitialspace=True, strict=True)
    fieldnames = next(reader)

    # remove matching columns but keep "DEVICE NAME 1" and "TYPE USER ASSOCIATION 1"
    keep_1st_few = {'DEVICE NAME', 'TYPE USER ASSOCIATION'}
    col_idx_to_remove = {i
                         for i, field in enumerate(fieldnames)
                         if ((m := col_re.match(field)) and
                             (m.group(1) not in keep_1st_few or int(m.group(2)) > max_devices))}

    out_file = io.StringIO()
    csv_writer = csv.writer(out_file, delimiter=',', doublequote=True,
                            escapechar=None, quotechar='"', quoting=csv.QUOTE_MINIMAL, skipinitialspace=True,
                            strict=True)
    col_idx_to_keep = [i for i in range(len(fieldnames)) if i not in col_idx_to_remove]
    csv_writer.writerow([fieldnames[i] for i in col_idx_to_keep])

    print(f'removing {len(col_idx_to_remove)} columns: ', end='', flush=True)
    for row in progress(reader):
        csv_writer.writerow([row[i] for i in col_idx_to_keep])
    print()
    out_file.seek(0)
    return out_file




@contextmanager
def open_output_tar(tar_file: str, read_only: bool) -> Optional[TarFile]:
    """
    Conditionally open a TAR file for writing
    """
    if read_only:
        yield None
        return
    with TarFile(name=tar_file, mode='w') as out:
        yield out
    return


def transform():
    """
    Main: transform given TAR file
    """
    parser = ArgumentParser(description='Transform a UCM config export TAR file by applying transformations to the CSV '
                                        'files within it')
    parser.add_argument('tar_file', help='the TAR file to transform')
    parser.add_argument('--readonly', action='store_true', help='do not write the transformed TAR file')
    parser.add_argument('--maxdevices', type=int, help='maximum number of DEVICE NAME columns to keep. Default: 5', default=5)

    args = parser.parse_args()
    input_tar = args.tar_file
    read_only = args.readonly
    max_devices = args.maxdevices

    # definition of transforms to apply to CSV files
    csv_transforms: dict[str, list[Callable[[TextIOBase], TextIOBase]]] = {
        'enduser.csv': [partial(remove_fields, fields_to_remove=ENDUSER_CSV_EXCLUDED_FIELDS, max_devices=max_devices)],
        'phone.csv': [partial(remove_fields, fields_to_remove=PHONE_CSV_EXCLUDED_FIELDS)]}

    if not os.path.isfile(input_tar):
        raise ValueError(f'{input_tar} is not a file')
    with TarFile(name=input_tar, mode='r') as tar:
        # filename for the transformed TAR file
        out_tar = f'{os.path.splitext(input_tar)[0]}_transformed.tar'

        # conditionally open the output TAR file
        with open_output_tar(out_tar, read_only) as out:
            # iterate over the members of the TAR file
            for member in tar.getmembers():
                member: tarfile.TarInfo
                # check if transformations are defined for this file
                if transformers := csv_transforms.get(member.name):
                    print(f'transforming {member.name}', flush=True)
                    if read_only:
                        continue
                    file = TextIOWrapper(tar.extractfile(member=member.name), encoding='utf-8')
                    for transformer in transformers:
                        transformed = transformer(file)
                        file.close()
                        file = transformed
                    bytes_io = io.BytesIO(file.read().encode('utf-8'))
                    file.close()
                    ti = tarfile.TarInfo(name=member.name)
                    ti.size = len(bytes_io.getvalue())
                    # set mtime to current time
                    ti.mtime = int(time.time())
                    bytes_io.seek(0)
                    out.addfile(ti, bytes_io)
                    bytes_io.close()
                else:
                    # no transformers -> copy as is
                    print(f'copying {member.name} as is', flush=True)
                    if read_only:
                        continue
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
