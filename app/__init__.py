from ucmexport import *
from user_dependency_graph import UserGraph
import logging
from typing import List, Dict, Set, Tuple, Iterable, Optional
from itertools import chain
from collections import defaultdict, Counter, namedtuple
import plotly.graph_objects as go
import plotly.express as px
import digit_analysis

from time import perf_counter

__all__ = ['App']

log = logging.getLogger(__name__)

"""
Aspects to consider to identify groups:
    shared line - X
    line group - X
    hunt list - X
    directed/indirect park
    intercom (phones with a phone button template that has a intercom line)
    IPMA
    blf - X
    Call-Park; All phones with access to call park partition can park calls and all users who can dial that number 
    range (have access to the same partition) can pick up a acall 
    call pickup (within group), DNs have a call pickup group asignment
    call pickup outside group
    user
"""

SUPPORTED_DEVICES = {'Cisco 8831', 'Cisco 8841', 'Cisco 8851', 'Cisco 8861', 'Cisco 8821', 'Cisco 8811', 'Cisco 8845',
                     'Cisco 8865', 'Cisco 8851NR', 'Cisco 8865NR', 'Cisco 8832', 'Cisco 8832NR'}


class SunBurstHelper:
    def __init__(self):
        self.ids = []
        self.labels = []
        self.parents = []
        self.values = []

    def add_entry(self, parent_id, label, value=1) -> int:
        new_id = len(self.ids)
        self.ids.append(new_id)
        self.labels.append(label)
        self.parents.append(parent_id)
        self.values.append(value)
        return new_id

    def add_phone(self, parent_id: int, phone: Phone, phone_childs):
        phone_id = self.add_entry(parent_id=parent_id, label=phone.device_name)
        if phone_childs:
            phone_childs(self, phone_id, phone)

    def add_phones(self, parent_id: int, phones: Iterable[Phone], details=False, phone_childs=None):
        phones_by_type: Dict[str, List[Phone]] = defaultdict(list)
        for phone in phones:
            phones_by_type[phone.device_type].append(phone)
        phone_types = sorted(phones_by_type, key=lambda pt: len(phones_by_type[pt]), reverse=True)
        for phone_type in phone_types:
            phone_type_id = self.add_entry(parent_id=parent_id, label=phone_type,
                                           value=len(phones_by_type[phone_type]))
            if details:
                for phone in sorted(phones_by_type[phone_type], key=lambda x: x.device_name):
                    self.add_phone(parent_id=phone_type_id, phone=phone, phone_childs=phone_childs)
        return

    def fig(self):
        fig = go.Figure(go.Sunburst(
            ids=self.ids,
            labels=self.labels,
            parents=self.parents,
            values=self.values
        ))
        return fig


class App:
    class menu_register:
        """"
        Decorate methods as menu items
        """
        menu_items = []

        def __init__(self, text):
            self.text = text

        def __call__(self, f):
            self.menu_items.append((self.text, f))
            return f

    def menu_quit(self):
        self.stopped = True

    def run(self):
        self.menu_register.menu_items.append(('Quit', App.menu_quit))
        while not self.stopped:
            # print menu
            print(f'selected tar file: {self.tar_files[self.tar_file_index]}')
            user_grouping = ", ".join(self.USER_RELATION_TEXT[r]
                                      for r in sorted(self.phone_relations_check))
            print(f'user grouping based on: {user_grouping}')
            print(f'only new relations: {self.only_new_relations}')
            for i, (text, _) in enumerate(self.menu_register.menu_items, 1):
                print(f'{i}) {text}')

            # get user input
            # noinspection PyUnboundLocalVariable
            choice = input(f'Enter your choice [1-{i}] : ')
            try:
                choice = int(choice)
            except ValueError:
                continue
            if choice < 1 or choice > i:
                continue

            # execute the registered method
            self.menu_register.menu_items[choice - 1][1](self)
            print()
            print()
        return

    # device types to ignore when looking at user assignments
    ANONYMOUS_DEVICE_TYPES = {
        'Cisco VGC Phone',
        'CTI Port',
        'Cisco ATA 186',
        'Analog Phone',
        'Cisco ATA 187',
        'Cisco Cius',
        'Universal Device Template'}

    USER_RELATION_SHARED_PHONES = 0
    USER_RELATION_SHARED_LINES = 1
    USER_RELATION_HUNT_PILOT = 2
    USER_RELATION_BLF = 3
    USER_RELATION_CPG = 4
    USER_RELATION_ALL = {USER_RELATION_SHARED_PHONES,
                         USER_RELATION_SHARED_LINES,
                         USER_RELATION_HUNT_PILOT,
                         USER_RELATION_BLF,
                         USER_RELATION_CPG}
    USER_RELATION_TEXT = {
        USER_RELATION_SHARED_PHONES: 'shared phones',
        USER_RELATION_SHARED_LINES: 'shared lines',
        USER_RELATION_HUNT_PILOT: 'hunt pilots',
        USER_RELATION_BLF: 'blfs',
        USER_RELATION_CPG: 'call pickup groups'
    }

    def __init__(self, tar_files: List[str]):
        self.stopped = False
        self.tar_files = tar_files
        self.tar_file_index = 0
        self.proxy = Proxy(tar=self.tar_files[self.tar_file_index])
        self.phone_relations_check = self.USER_RELATION_ALL
        self.only_new_relations = False
        self.user_graph: Optional[UserGraph] = None

    @menu_register('Switch tar file')
    def menu_switch_tar_file(self):
        self.user_graph = None
        self.tar_file_index += 1
        if self.tar_file_index >= len(self.tar_files):
            self.tar_file_index = 0
        self.proxy = Proxy(tar=self.tar_files[self.tar_file_index])

    @menu_register('Toggle "only new relations"')
    def toggle_only_new_relations(self):
        self.only_new_relations = not self.only_new_relations

    def toggle_check(self, check):
        self.user_graph = None
        if check in self.phone_relations_check:
            self.phone_relations_check.remove(check)
        else:
            self.phone_relations_check.add(check)

    @menu_register('Toggle "shared phones"')
    def menu_toggle_shared_phones(self):
        self.toggle_check(self.USER_RELATION_SHARED_PHONES)

    @menu_register('Toggle "shared lines"')
    def menu_toggle_shared_lines(self):
        self.toggle_check(self.USER_RELATION_SHARED_LINES)

    @menu_register('Toggle "hunt pilot"')
    def menu_toggle_hunt_pilot(self):
        self.toggle_check(self.USER_RELATION_HUNT_PILOT)

    @menu_register('Toggle "blf"')
    def menu_toggle_blf(self):
        self.toggle_check(self.USER_RELATION_BLF)

    @menu_register('Toggle "call pickup groups"')
    def menu_toggle_cpg(self):
        self.toggle_check(self.USER_RELATION_CPG)

    def assert_user_graph(self):
        if self.user_graph is not None:
            return
        self.user_graph = UserGraph()
        if self.USER_RELATION_HUNT_PILOT in self.phone_relations_check:
            # Now let's look at all hunt pilots, and link all users of phones with dns in any hunt-list
            users_added = self.user_graph.related_users_hunt_pilot(proxy=self.proxy)
            print(f'{users_added} based on hunt pilots')

        if self.USER_RELATION_SHARED_PHONES in self.phone_relations_check:
            # Shared phones
            users_added = self.user_graph.related_users_shared_phones(self.proxy,
                                                                      only_new_relations=self.only_new_relations)
            print(f'{users_added} users based on shared phones')

        if self.USER_RELATION_SHARED_LINES in self.phone_relations_check:
            # we now want to check all dns of all phones and if that dn might be shared with phones belonging
            # to other users
            users_added = self.user_graph.related_users_shared_lines(self.proxy,
                                                                     only_new_relations=self.only_new_relations)
            print(f'{users_added} based on shared lines')

        # also users with BLFs on other users' DNs are related
        if self.USER_RELATION_BLF in self.phone_relations_check:
            users_added = self.user_graph.related_users_blf(proxy=self.proxy,
                                                            only_new_relations=self.only_new_relations)
            print(f'{users_added} user relations based on BLF')

        if self.USER_RELATION_CPG in self.phone_relations_check:
            users_added = self.user_graph.related_users_cpg(proxy=self.proxy,
                                                            only_new_relations=self.only_new_relations)
            print(f'{users_added} user relations based on CPG')
        self.user_graph.simplify()

    @menu_register('User dependency')
    def menu_user_dependency(self):
        self.user_graph = None
        self.assert_user_graph()
        # print stats about clusters
        print()
        print('Summary:')
        related_users = self.user_graph.related_users_by_len()
        for cluster_len in sorted(related_users):
            print(f'{len(related_users[cluster_len])} groups of users with {cluster_len} users each')
        print(f'total: {sum(map(len, related_users.values()))} groups')
        no_users = sum(sum(len(cluster)
                           for cluster in clusters)
                       for clusters in related_users.values())
        print(f'total: {no_users} users')

    @menu_register('Draw user dependency')
    def menu_draw_user_clusters(self):
        """
        Create a graph of users
        :return: None
        """
        self.assert_user_graph()
        self.user_graph.draw()

    @menu_register('Phones without lines')
    def menu_phones_no_lines(self):
        phones_no_lines = [phone for phone in self.proxy.phones.list if len(phone.lines) == 0]
        device_types = Counter(phone.device_type for phone in phones_no_lines)
        print('Phones w/o lines')
        ll = max(len(f'{c}') for c in device_types.values())
        dtl = max(len(dt) for dt in device_types)
        for device_type in sorted(device_types):
            output = ", ".join(phone.device_name for phone in phones_no_lines if phone.device_type == device_type)
            print(f'{device_types[device_type]:{ll}} x {device_type:{dtl}}: {output}')

    @menu_register('Device type stats')
    def menu_device_type_stats(self):
        device_type_counter = Counter(p.device_type for p in self.proxy.phones.list)
        device_types = list(device_type_counter)
        device_types.sort()
        max_len = max(len(dt) for dt in device_types)
        for device_type in device_types:
            print(f'{device_type:{max_len}}: {device_type_counter[device_type]:5} '
                  f'{"supported" if device_type in SUPPORTED_DEVICES else "unsupported"}')
        print('Supported/unsupported classification only based on device type')

    @menu_register('Supported vs. unsupported phones for migration')
    def menu_supported_phones(self):
        phones = self.proxy.phones.list
        # we can ignore phones with certain device types
        relevant_phones = [phone for phone in phones if phone.device_type not in self.ANONYMOUS_DEVICE_TYPES]

        sb = SunBurstHelper()
        sb_data = {
            'supported': defaultdict(list),
            'unsupported': defaultdict(list)
        }
        for phone in relevant_phones:
            if phone.device_type in SUPPORTED_DEVICES:
                sb_key = 'supported'
            else:
                sb_key = 'unsupported'
            sb_data[sb_key][phone.device_type].append(phone.device_name)
        for sb_key in sb_data:
            parent = sb.add_entry(parent_id='', label=sb_key, value=len(sb_data[sb_key]))
            for device_type in sb_data[sb_key]:
                device_parent = sb.add_entry(parent_id=parent, label=device_type,
                                             value=len(sb_data[sb_key][device_type]))
                for device_name in sb_data[sb_key][device_type]:
                    sb.add_entry(parent_id=device_parent, label=device_name)
        if len(sb.ids) > 10000:
            print(f'figure with {len(sb.ids)} nodes might be hard to render...')
        fig = sb.fig()
        fig.update_layout(margin=dict(t=0, l=0, r=0, b=0))
        fig.show()

    @menu_register('Analyze phone/user assignment')
    def menu_analyze_phone_user_assignment(self):
        # phones have owners and USER ID X (x=1...N)
        phones = self.proxy.phones.list

        relevant_phones = []
        ignored_phones = []
        for phone in phones:
            if phone.device_type in self.ANONYMOUS_DEVICE_TYPES:
                ignored_phones.append(phone)
            else:
                relevant_phones.append(phone)

        sb = SunBurstHelper()
        phones_id = sb.add_entry(parent_id='', label='Phones')
        relevant_id = sb.add_entry(parent_id=phones_id, label='relevant', value=len(relevant_phones))
        ignored_id = sb.add_entry(parent_id=phones_id, label='ignored', value=len(ignored_phones))
        sb.add_phones(ignored_id, ignored_phones)

        # we can ignore phones with certain device types
        relevant_phones = [phone for phone in phones if phone.device_type not in self.ANONYMOUS_DEVICE_TYPES]

        # classifications per phone
        # '0': no user
        # '1': exactly one user
        # 'n': more than one user
        # 'u': at least unknown user
        phone_classification: Dict[str, Set[str]] = defaultdict(set)
        for phone in relevant_phones:
            device_name = phone.device_name
            users = phone.user_set
            if len(users) == 0:
                phone_classification[device_name].add('0')
            elif len(users) == 1:
                phone_classification[device_name].add('1')
            else:
                phone_classification[device_name].add('n')
            # see if all users ids are valid
            if any((self.proxy.end_user.get(u) is None) for u in users):
                phone_classification[device_name].add('u')
        print(f'# of phones: {len(self.proxy.phones.list)}')
        print(f'# of ignored phones ({", ".join(self.ANONYMOUS_DEVICE_TYPES)}): '
              f'{len(self.proxy.phones.list) - len(relevant_phones)}')

        print('Phones with issues')
        print('0 : no user, n: more than one user, u: at least unknown user')
        phones_with_issues = {device_name: classification
                              for device_name, classification in phone_classification.items()
                              if classification & {'u', 'n', '0'}}

        ok_id = sb.add_entry(parent_id=relevant_id, label='Ok',
                             value=len(relevant_phones) - len(phones_with_issues))
        sb.add_phones(ok_id, phones=(p
                                     for p in relevant_phones
                                     if not phone_classification[p.device_name] & {'u', 'n', '0'}
                                     ))

        w_issues_id = sb.add_entry(parent_id=relevant_id, label='With issues', value=len(phones_with_issues))

        classification_to_text = {
            '0': 'No user',
            'n': 'Multiple users',
            'u': 'unknown user'
        }

        def sunburst_users(sb, parent_id, phone: Phone):
            users = phone.user_set
            if not users:
                return
            for user in users:
                sb.add_entry(parent_id=parent_id, label=user)

        for issue in '0nu':
            phones_with_this_issue = [self.proxy.phones[device_name]
                                      for device_name, classification in phones_with_issues.items()
                                      if issue in classification]
            class_id = sb.add_entry(parent_id=w_issues_id, label=classification_to_text[issue],
                                    value=len(phones_with_this_issue))
            sb.add_phones(parent_id=class_id, phones=phones_with_this_issue, details=True,
                          phone_childs=sunburst_users)

            phones_with_issue_by_device_type: Dict[str, List[Phone]] = defaultdict(list)
            for phone in phones_with_this_issue:
                phones_with_issue_by_device_type[phone.device_type].append(phone)

            print(f'  Phones classified as "{issue}"')
            device_types = sorted(phones_with_issue_by_device_type)
            for device_type in device_types:
                output = (f'{phone.device_name}' for phone in phones_with_issue_by_device_type[device_type])
                print(f'    {len(phones_with_issue_by_device_type[device_type])} x {device_type}: '
                      f'{", ".join(output)}')

        fig = sb.fig()
        fig.update_layout(margin=dict(t=0, l=0, r=0, b=0))
        fig.show()

        log.debug('Start looking at phones per user')
        # Check whether the 1st line on all phones of a user has the same DN
        # get phones per user
        phones_per_user: Dict[str, List[Phone]] = defaultdict(list)
        for phone in self.proxy.phones.list:
            users = list(phone.user_set)
            if len(users) != 1:
                # we only want to look at phones with one user
                continue
            user = users[0]
            phones_per_user[user].append(phone)
        log.debug('Done looking at phones per user')

        def dn_and_partition1(phone: Phone) -> Optional[str]:
            try:
                return phone.lines[1].dn_and_partition
            except KeyError:
                return None

        log.debug('Start looking at all lines of all phones')
        dn_issues = {user: phones
                     for user, phones in phones_per_user.items()
                     if not (dn := dn_and_partition1(phones[0])) or
                     any(dn != dn_and_partition1(phone) for phone in phones[1:])}
        log.debug('Done looking at all lines of all phones')
        print('Users with inconsistent DN assignments')
        for user in sorted(dn_issues):
            phones = dn_issues[user]
            output = ', '.join(f'{phone.device_name}({dn_and_partition1(phone)})' for phone in phones)
            print(f'{user}: {output}')

    @menu_register('External phone number masks')
    def menu_external_phone_number_masks(self):
        phones_by_mask: Dict[str, List[Phone]] = defaultdict(list)
        for phone in self.proxy.phones.list:
            line = next((line for line in phone.lines.values()), None)
            if not line:
                continue
            mask = line.external_phone_number_mask
            if not mask:
                continue
            phones_by_mask[mask].append(phone)
        sb = SunBurstHelper()
        root = sb.add_entry(parent_id='', label='External Phone Number Masks')
        for mask in sorted(phones_by_mask):
            phones_this_mask = phones_by_mask[mask]
            print(f'mask {mask}: {len(phones_this_mask)} phones')
            mask_id = sb.add_entry(parent_id=root, label=mask, value=len(phones_this_mask))
            sb.add_phones(parent_id=mask_id, phones=phones_this_mask)
        fig = sb.fig()
        fig.show()

    @menu_register('DN analyis')
    def menu_dn_analysis(self):
        """
        get all DNs of all 1st lines of all phones and analyze the structure
        :return: None
        """
        DNP = namedtuple('DNP', ['dn', 'partition'])
        dnps = [DNP._make((line1.directory_number, line1.partition))
                for phone in self.proxy.phones.list
                if (line1 := phone.lines.get(1))]

        def do_analysis(dnps: List[DNP]):
            """
            Analysis of a set of DNs
            :param dnps:
            :return:
            """
            # group DNs by len
            dn_by_len: Dict[int, List[str]] = defaultdict(list)
            for dnp in dnps:
                dn_by_len[len(dnp.dn)].append(dnp.dn)

            DNCluster = namedtuple('DNCluster', ['prefix', 'dns'])

            def find_clusters(prefix: str, digit_strings: List[str], total_count=None) -> List[Tuple[str, List[str]]]:
                if not prefix:
                    total_count = len(digit_strings)
                if len(digit_strings[0]) <= 1:
                    return []

                # determine DNs per next level digit
                first_digits = set()
                next_level_dns: Dict[str, List[str]] = defaultdict(set)
                for ds in digit_strings:
                    first_digit = ds[0]
                    first_digits.add(first_digit)
                    next_level_dns[first_digit].add(ds[1:])
                first_digits = sorted(first_digits)
                total_count /= len(first_digits)
                for fd in first_digits:
                    nld = sorted(next_level_dns[fd])[:10]
                    output = [f'{prefix}{fd}-{ds}' for ds in nld]
                    if len(next_level_dns[fd]) > 10:
                        output.append('...')
                    remaining_length = len(next(dn for dn in next_level_dns[fd]))
                    density = 9 ** remaining_length

                    print(
                        f'prefix {prefix}-{fd}: {int(total_count)} {len(next_level_dns[fd])}/{density} digit strings: '
                        f'{", ".join(output)}')
                for fd in first_digits:
                    find_clusters(prefix=f'{prefix}{fd}', digit_strings=list(next_level_dns[fd]),
                                  total_count=total_count)

                return []

            for dn_len in dn_by_len:
                print(f'  len({dn_len}):')
                find_clusters('', dn_by_len[dn_len])
            return []

        # analysis of all DNS
        print('All DNs')
        do_analysis(dnps)

        dn_by_partition: Dict[str, List[DNP]] = defaultdict(list)
        for dnp in dnps:
            dn_by_partition[dnp.partition].append(dnp)

        # analysis by partition
        for partition in dn_by_partition:
            print(f'Partition \'{partition}\'')
            do_analysis(dn_by_partition[partition])

    @menu_register('Find Locations based on users phone numbers')
    def menu_locations_based_on_users_phones(self):
        # assert CSVs are read
        # noinspection PyStatementEffect
        self.proxy.phones.list
        # noinspection PyStatementEffect
        self.proxy.end_user.list

        print(f'                       # of phones: {len(self.proxy.phones.list)}')

        # Ignore "anonymous" phones
        relevant_phones = [phone
                           for phone in self.proxy.phones.list
                           if phone.device_type not in self.ANONYMOUS_DEVICE_TYPES]
        print(f'              w/o anonymous phones: {len(relevant_phones)}')

        # ignore phones w/o users or with multiple users
        relevant_phones = [phone
                           for phone in relevant_phones
                           if len(phone.user_set) == 1]
        print(f'         only phones with one user: {len(relevant_phones)}')

        # ignore phones where the users don't exist
        relevant_phones = [phone
                           for phone in relevant_phones
                           if self.proxy.end_user.get(list(phone.user_set)[0])]
        print(f' only phones where the user exists: {len(relevant_phones)}')

        # ignore phones w/o lines
        relevant_phones = [phone
                           for phone in relevant_phones
                           if len(phone.lines)]
        print(f'only phones with at least one line: {len(relevant_phones)}')

        users = list(chain.from_iterable(phone.user_set
                                         for phone in relevant_phones))
        # check if
        device_name_len = max(len(phone.device_name) for phone in relevant_phones)
        uid_len = max(len(u) for u in users)
        for phone in relevant_phones:
            user_id = list(phone.user_set)[0]
            user = self.proxy.end_user[user_id]
            user_phone_number = user.phone.replace(' ', '')
            if not user_phone_number:
                user_phone_number = 'empty'

            try:
                dn = phone.lines[1].directory_number
            except KeyError:
                dn = 'no line!'
            print(f'{phone.device_name:{device_name_len}} {user_id:{uid_len}} {user_phone_number} {dn}')

        dns = [line1.directory_number for phone in relevant_phones if (line1 := phone.lines.get(1))]
        dns_by_len: Dict[int, List[str]] = defaultdict(list)
        for dn in dns:
            dns_by_len[len(dn)].append(dn)

        for dn_len, dns_work in dns_by_len.items():
            print(f'len {dn_len}: {len(dns_work)}')

            for prefix_len in range(1, dn_len + 1):
                prefixes = sorted(list(set(dn[:prefix_len] for dn in dns_work)))
                if len(prefixes) > 15:
                    prefixes_output = prefixes[:15] + ['...']
                else:
                    prefixes_output = prefixes
                print(f'  len {prefix_len}: {len(prefixes)} prefixes: {", ".join(prefixes_output)}')

        def search_location_prefixes(dn_len, prefix_len, dns):
            prefixes = sorted(list(set(dn[:prefix_len] for dn in dns)))

            pass

        for dn_len, dns_work in dns_by_len.items():
            search_location_prefixes(dn_len=dn_len, prefix_len=1, dns=dns_work)

    @menu_register('Sankey Diagram of DNs')
    def menu_sankey_dn(self):
        # get all DNs from the 1st line of all phones
        dns = [line1.directory_number
               for phone in self.proxy.phones.list
               if (line1 := phone.lines.get(1))]

        node_label = []
        links_source = []
        link_target = []
        link_value = []

        def add_to_sankey(numbers: List[str], parent_node_id: int = None):
            first_digits = sorted(set(n[0] for n in numbers))
            for first_digit in first_digits:
                node_id = len(node_label)
                label = first_digit
                if parent_node_id is not None:
                    label = f'{node_label[parent_node_id].strip("X")}{label}'
                # noinspection PyUnboundLocalVariable
                next_level_numbers = [s for n in numbers if n[0] == first_digit and (s := n[1:])]
                if not next_level_numbers:
                    node_label.append(label)
                    continue
                max_len = max(map(len, next_level_numbers))
                node_label.append(f'{label}{"X" * max_len}')
                if max_len < 2:
                    continue
                if next_level_numbers and parent_node_id is not None:
                    links_source.append(parent_node_id)
                    link_target.append(node_id)
                    link_value.append(len(next_level_numbers))
                add_to_sankey(next_level_numbers, parent_node_id=node_id)

        add_to_sankey(numbers=dns)
        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color='black',
                          width=0.5),
                label=node_label,
                color='blue'
            ),
            link=dict(
                source=links_source,
                target=link_target,
                value=link_value
            )
        )])
        fig.update_layout(title_text='Sankey', font_size=10)
        fig.show()

    @menu_register('Find intra-site dialing translation patterns')
    def menu_find_intrasite_translation_patterns(self):
        tps = self.proxy.translation_pattern.list
        print(f'Found {len(tps)} translation patterns')
        tp_by_len: Dict[int, List[TranslationPattern]] = defaultdict(list)
        names = []
        parents = []
        for tp in tps:
            if tp.block:
                # ignore blocking translation pattern
                continue
            tp_by_len[tp.length].append(tp)
            names.append(tp.pattern_and_partition)
            parents.append(str(tp.length))
        # add tp lengths as parents
        names.extend(map(str, tp_by_len))
        # .. w/o parents themselves
        parents.extend([''] * len(tp_by_len))
        fig = px.treemap(
            names=names,
            parents=parents
        )
        fig.show()

    @menu_register('CSS Combinations on first lines')
    def menu_css_combinations(self):
        css_combinations = Counter((first_line.css, phone.css)
                                   for phone in self.proxy.phones.list
                                   if (first_line := next(iter(phone.lines.values()), None)))
        frequency_len = len(f'{max(css_combinations.values())}')
        css_len = max(len(f'{", ".join(css_combination)}') for css_combination in css_combinations)
        for css_combination in sorted(css_combinations,
                                      key=lambda x: css_combinations[x],
                                      reverse=True):
            frequency = css_combinations[css_combination]
            combined_partitions = list(chain.from_iterable(map(self.proxy.css.partition_names, css_combination)))
            print(
                f'frequency: {frequency:{frequency_len}}: {", ".join(css_combination):{css_len}} -> '
                f'{":".join(combined_partitions)}')

    @menu_register('Dial Plan Analysis')
    def menu_dial_plan_analysis(self):
        da_tree = digit_analysis.DaNode.from_proxy(self.proxy,first_line_only=True)
        # after adding all patterns we now want to find out how to dial on-net
        # traverse the tree breadth first and consider all sub trees which potentially can get us to a DN
        # - only TPs and DNs
        # - look out for blocking TPs

        # get CSS combinations on phones
        # noinspection PyShadowingNames
        css_count = Counter((first_line.css, phone.css)
                            for phone in self.proxy.phones.list
                            if (first_line := next(iter(phone.lines.values()), None)))

        css_combinations = sorted(css_count, key=lambda c: css_count[c], reverse=True)
        for line_css_name, device_css_name in css_combinations:
            print(f'Looking at line_css:device_css: {line_css_name}:{device_css_name}')
            combined_partitions = list(chain(self.proxy.css.partition_names(line_css_name),
                                             self.proxy.css.partition_names(device_css_name)))
            # add <NONE> partition at the end if not already present somewhere in the partition list
            if next((p for p in combined_partitions if not p), None) is None:
                print(f'appending NONE partition')
                combined_partitions.append('')
            print(f'{line_css_name} + {device_css_name}: {", ".join(combined_partitions)}')
            leaves = list(da_tree.find_leaves(depth=30,
                                              pattern_types={digit_analysis.PatternType.DN,
                                                             digit_analysis.PatternType.TP},
                                              stop_decent={digit_analysis.PatternType.DN},
                                              partitions=combined_partitions))
            print(f'  {len(leaves)} leaves')
        # list all blocking TPs
        blocking_tps = [tp for tp in self.proxy.translation_pattern.list
                        if tp.block]
        print("\n".join(f'{tp}' for tp in blocking_tps))
        # print(da_tree.pretty())

    @menu_register('Translation pattern overview')
    def menu_translation_pattern_overview(self):
        tps = self.proxy.translation_pattern.list
        rows = [('pattern', 'partition', 'Urgent', 'Block', 'discard digits', 'prefix digits', 'mask')]
        for tp in tps:
            rows.append((f'{tp.pattern}', f'{tp.partition}', f'{tp.urgent}', f'{tp.block}', f'{tp.discard_digits}',
                         f'{tp.called_party_prefix_digits}', f'{tp.called_party_mask}'))
        transposed = list(zip(*rows))
        column_lens = [max(map(len, col)) for col in transposed]
        print("\n".join(' '.join(f'{c:{column_lens[i]}}' for i, c in enumerate(r)) for r in rows))

    @menu_register('Find abbreviated on-net dialing')
    def menu_abbreviated_on_net(self):
        """

        :return:
        """

        """For a given CSS find all TP terminal nodes for each terminal TP node apply TP's translation to TP's 
        pattern and then see if that transformed digit string can hit DNs """
        da_tree = digit_analysis.DaNode.from_proxy(self.proxy)

        css_count = Counter((first_line.css, phone.css)
                            for phone in self.proxy.phones.list
                            if (first_line := next(iter(phone.lines.values()), None)))

        css_combinations = sorted(css_count, key=lambda c: css_count[c], reverse=True)
        for line_css_name, device_css_name in css_combinations:
            print(f'Looking at line_css:device_css: {line_css_name}+{device_css_name}')
            combined_partitions = list(chain(self.proxy.css.partition_names(line_css_name),
                                             self.proxy.css.partition_names(device_css_name)))
            # add <NONE> partition at the end if not already present somewhere in the partition list
            if next((p for p in combined_partitions if not p), None) is None:
                print(f'appending NONE partition')
                combined_partitions.append('')
            print(f'{line_css_name}+{device_css_name}: {":".join(combined_partitions)}')
            # get all TPs that can be dialed with this CSS
            leaves = list(da_tree.find_leaves(depth=30,
                                              pattern_types={digit_analysis.PatternType.TP},
                                              partitions=combined_partitions))
            combined_css = ':'.join(combined_partitions)
            for da_node, dial_string in leaves:
                tps = [tp for tp in da_node.terminal_pattern.values() if isinstance(tp, digit_analysis.TranslationPattern)]
                for tp in tps:
                    print(f'{dial_string}: {tp.pattern}')
                    lookup_result = da_tree.lookup(digits=dial_string,css=combined_css)
                    print(f'Dial string {dial_string} lookup led to {lookup_result}')
                    #translated_dial_string, css = tp.translate(digits=tp.pattern.replace('.', ''), css=combined_partitions)
                    foo = 1
        pass