import os
import webbrowser
from itertools import chain
from collections import defaultdict
import logging
import networkx as nx
import plotly.graph_objects as go
from pydantic import BaseModel, model_validator

from ucmexport import *

from typing import Union, Set, Generator, Dict, List, Optional

log = logging.getLogger(__name__)

JS_TEMPLATE_3D = """
<head>
  <style> body { margin: 0; } </style>

  <script src="https://unpkg.com/3d-force-graph"></script>
  <!--<script src="../../dist/3d-force-graph.js"></script>-->
</head>

<body>
  <div id="3d-graph"></div>

  <script>
    const gData = {};

    const Graph = ForceGraph3D()
      (document.getElementById('3d-graph'))
        .nodeAutoColorBy('group')
        .linkOpacity(0.5)
        .linkCurvature(0.2)
        .linkCurveRotation(1)
        .linkDirectionalParticles(2)
        .graphData(gData)
        .onNodeClick(node => {
          // Aim at node from outside it
          const distance = 40;
          const distRatio = 1 + distance/Math.hypot(node.x, node.y, node.z);

          const newPos = node.x || node.y || node.z
            ? { x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio }
            : { x: 0, y: 0, z: distance }; // special case if node is in (0,0,0)

          Graph.cameraPosition(
            newPos, // new position
            node, // lookAt ({ x, y, z })
            3000  // ms transition duration
          );
        });
  </script>
</body>
"""


class GDataNode(BaseModel):
    id: str
    name: str
    group: Optional[str] = None




class GDataLink(BaseModel):
    source: str
    target: str

    @model_validator(mode='after')
    def val_node(self):
        source_type = self.source.split()[0]
        target_type = self.target.split()[0]
        # user is always a target
        if source_type == 'user':
            self.source, self.target = self.target, self.source
        # dn is always a source
        if target_type == 'dn':
            self.source, self.target = self.target, self.source
        return self


class GData(BaseModel):
    nodes: list[GDataNode]
    links: list[GDataLink]


class UserGraph(nx.Graph):

    @staticmethod
    def user_node(user: Union[str, EndUser]):
        if isinstance(user, str):
            return f'user {user}'
        return f'user {user.user_id}'

    def user_node_by_id(self, uid: str, proxy: Proxy):
        user = proxy.end_user.get(uid)
        if user is None:
            return user
        return self.user_node(user)

    @staticmethod
    def phone_node(phone: Phone):
        return f'phone {phone.device_name}'

    @staticmethod
    def hunt_pilot_node(hp: HuntPilot):
        return f'huntpilot {hp.pilot_and_partition}'

    @staticmethod
    def cpg_node(cpg: Union[str, CallPickupGroup]):
        if isinstance(cpg, str):
            return f'CPG {cpg}'
        return f'CPG {cpg.name}'

    @staticmethod
    def ignore_uid(proxy: Proxy) -> set[str]:
        # we want to ignore users that own an excessive number of phones
        phones_per_user: dict[str, int] = defaultdict(int)
        for phone in proxy.phones.list:
            for user in phone.user_set:
                phones_per_user[user] += 1
        ignore_uid = {uid for uid, count in phones_per_user.items() if count > 20}
        print(f'ignoring {len(ignore_uid)} users with more than 20 phones: {", ".join(sorted(ignore_uid))}')
        return ignore_uid

    def connected_user_nodes(self, node: str) -> Set[str]:
        """
        Determine all user nodes connected to given node
        :param node: node to search connected user nodes for
        :return: set of connected user nodes
        """
        try:
            connected = nx.algorithms.node_connected_component(self, node)
        except KeyError:
            return set()
        return set(c for c in connected if c.startswith('user'))

    def connected_user_ids(self, user_id: str) -> Set[str]:
        """
        Determine user ids of users already connected to a user with a given id
        :param user_id: user id
        :return: set of ids of connected users
        """
        connected = self.connected_user_nodes(f'user {user_id}')
        return set(c[5:] for c in connected)

    def add_path(self, *nodes: str):
        p_node = None
        for node in nodes:
            self.add_node(node)
            if p_node:
                self.add_edge(p_node, node)
            p_node = node

    def related_users_hunt_pilot(self, proxy: Proxy) -> int:
        """
        Add user relations to graph: users related via hunt pilot
        :param proxy:
        :return:
        """
        print('Related users based on hunt pilots...')
        users_added = 0
        ignore_uid = self.ignore_uid(proxy)
        for hunt_pilot in proxy.hunt_pilot.list:
            hp_node = self.hunt_pilot_node(hunt_pilot)
            # all patterns:partitions on all line groups
            dnps = hunt_pilot.pattern_and_partition_set(proxy.hunt_pilot)
            # now we want to get the set of users on all phones with these dns
            # start with all phones that have any of these dns
            phones = set(chain.from_iterable(proxy.phones.by_dn_and_partition.get(dnp, []) for dnp in dnps))
            # finally get all users associated with these phones
            user_ids = set(chain.from_iterable(phone.user_set for phone in phones))
            user_ids -= ignore_uid
            # .. and we only want to look at users which actually exist as end users
            users = [user for user_id in user_ids
                     if (user := proxy.end_user.get(user_id))]
            if len(users) < 2:
                continue
            # add node for hunt pilot to graph
            self.add_node(hp_node)
            # now for each user add a node and create a link between hunt pilot and user
            for user in users:
                un = self.user_node(user)
                self.add_node(un)
                self.add_edge(hp_node, un)
            users_added += (len(users) - 1)
            # for
        # for
        return users_added

    def related_users_shared_phones(self, proxy: Proxy, only_new_relations=False) -> int:
        """
        Find users that are related based on shared phones
        :param proxy:
        :param only_new_relations:
        :return: number of related users
        """
        users_added = 0
        print('Related users based on shared phones...')
        ignore_uid = self.ignore_uid(proxy)
        for phone in proxy.phones.list:
            # only consider actually existing end users
            user_node_set = {self.user_node(user)
                             for uid in phone.user_set
                             if (uid not in ignore_uid) and (user := proxy.end_user.get(uid))}
            if len(user_node_set) < 2:
                continue
            # no need to add if all users are already connected
            if only_new_relations:
                not_connected_per_user = [user_node_set - {user_node} - self.connected_user_nodes(user_node)
                                          for user_node in user_node_set]
                if not any(not_connected_per_user):
                    continue

            # add a node for the phone
            pn = self.phone_node(phone)
            # self.add_node(pn)
            # for each user add a node and an edge between phone and user
            for user_node in user_node_set:
                users_added += 1
                self.add_node(user_node)
                self.add_edge(user_node, pn)
        return users_added

    def related_users_shared_lines(self, proxy: Proxy,
                                   only_first_phone=True,
                                   only_first_dnp=True,
                                   only_new_relations=False) -> int:
        print('Related users based on shared lines...')
        ignore_uid = self.ignore_uid(proxy)

        # get all users and the user's DNs from the users phones
        phones_by_user_id = proxy.phones.by_user_id
        dnps_by_user_id = {user_id: dnps
                           for user_id, phones in phones_by_user_id.items()
                           if ((user_id not in ignore_uid) and
                               (dnps := chain.from_iterable((line.dn_and_partition
                                                             for line in phone.lines.values())
                                                            for phone in phones)))}
        # for each user id and DN get phones with different users
        phones_by_dn_and_partition = proxy.phones.by_dn_and_partition
        phones_other_users_by_user_and_dnp = {user_id: phones_other_users_by_dn
                                              for user_id, dnps in dnps_by_user_id.items()
                                              if ((user_id not in ignore_uid) and
                                                  (phones_other_users_by_dn :=
                                                   {dnp: phones
                                                    for dnp in dnps
                                                    if (phones := [phone
                                                                   for phone in phones_by_dn_and_partition[dnp]
                                                                   if (phone.user_set - {user_id} - ignore_uid)])}))}

        users_added = 0
        for user_id, phones_other_user_by_dnp in phones_other_users_by_user_and_dnp.items():
            other_users = set(chain.from_iterable(chain.from_iterable(phone.user_set
                                                                      for phone in phones)
                                                  for phones in phones_other_user_by_dnp.values()))
            other_users -= {user_id}
            other_users -= ignore_uid
            # we don't need to look at users that are already connected
            if only_new_relations:
                connected_users = self.connected_user_ids(user_id)
                if connected_users:
                    other_users -= connected_users
            other_users = sorted(other_users)
            # for each other user (greater than the current user) and dnp get a list of DNs with list of phones
            # this user is on
            # we ignore phones the current user is one b/c that is the simple case of a shared phone which is
            # handled separately
            phones_by_other_user_and_dnp = {other_user_id: {dnp: phones_other_user
                                                            for dnp, phones in phones_other_user_by_dnp.items()
                                                            if (phones_other_user :=
                                                                [phone
                                                                 for phone in phones
                                                                 if other_user_id in phone.user_set
                                                                 and user_id not in phone.user_set])}
                                            for other_user_id in other_users
                                            if other_user_id > user_id}
            for other_user_id in sorted(phones_by_other_user_and_dnp):
                phones_by_dnp = phones_by_other_user_and_dnp[other_user_id]
                for dnp in sorted(phones_by_dnp):
                    phones = phones_by_dnp[dnp]
                    own_phone_with_dn = next(phone
                                             for phone in sorted(inner_phone
                                                                 for inner_phone in
                                                                 proxy.phones.by_dn_and_partition[dnp]
                                                                 if user_id in inner_phone.user_set))
                    for phone in phones:
                        # create path
                        # user_id-first_owned_phone_with_dnp-dnp-phone-other_user
                        self.add_path(self.user_node_by_id(user_id, proxy),
                                      self.phone_node(own_phone_with_dn),
                                      f'dn {dnp}',
                                      self.phone_node(phone),
                                      self.user_node_by_id(other_user_id, proxy))
                        users_added += 1
                        if only_first_phone:
                            break
                    # for phone ..
                    if only_first_dnp:
                        break
                # for dnp ...
            # for other_user_id ...
        # for user_id ..
        return users_added

    def not_used_related_users_shared_lines(self, proxy: Proxy) -> int:
        users_added = 0
        for phone in proxy.phones.list:
            users = phone.user_set
            dnps = [line.dn_and_partition for line in phone.lines.values()]
            # for each DN get the list of phones this DN is provisioned on and look whether any phone has a different
            # user
            for dnp in dnps:
                other_phones = [p
                                for p in proxy.phones.by_dn_and_partition[dnp]
                                if p != phone]
                if not other_phones:
                    # no need to look further if this is the only phone
                    continue
                # this is the node for the dn (in case we need it)
                dn_node = f'dn {dnp}'
                for other_phone in other_phones:
                    # only add if the other phone has at least one different users
                    other_users = other_phone.user_set - users
                    if not other_users:
                        continue
                    for user in users:
                        un = self.user_node_by_id(uid=user, proxy=proxy)
                        if not un:
                            # this user does not exist?
                            continue
                        for other_user in other_users:
                            oun = self.user_node_by_id(uid=other_user, proxy=proxy)
                            if not oun:
                                continue
                            users_added += 1
                            # nodes for users
                            self.add_node(un)
                            self.add_node(oun)

                            # node for DN
                            self.add_node(dn_node)

                            # phone and edges for phone
                            # user-phone-dn
                            pn = self.phone_node(phone)
                            self.add_node(pn)
                            self.add_edge(un, pn)
                            self.add_edge(pn, dn_node)

                            # phone and edges for other phone
                            # user-phone-dn
                            opn = self.phone_node(other_phone)
                            self.add_node(opn)
                            self.add_edge(oun, opn)
                            self.add_edge(opn, dn_node)
                        # for
                    # for
                # for
            # for
        # for
        return users_added

    def related_users_blf(self, proxy: Proxy, only_new_relations=False) -> int:
        """
        Identify users related via BLF monitoring (one user monitors DNs on another user's phone)
        :param proxy: CSV proxy
        :param only_new_relations: only a add user relations for users not already in the graph as related
        :return: number of users added to the graph
        """
        print('related users based on BLF...')
        users_added = 0
        phones_by_user_id = proxy.phones.by_user_id
        ignore_uuid = self.ignore_uid(proxy)
        for user_id in phones_by_user_id:
            if user_id in ignore_uuid:
                continue
            if proxy.end_user.get(user_id) is None:
                log.warning(f'user {user_id} does not exist')
                continue
            for phone in phones_by_user_id[user_id]:
                for blf_dnp in (blf.dn_and_partition
                                for blf in phone.busy_lamp_fields.values()):
                    # on which phones does this dnp exist...
                    monitored_phones = proxy.phones.by_dn_and_partition.get(blf_dnp, [])
                    for monitored_phone in monitored_phones:
                        monitored_user_ids = monitored_phone.user_set
                        for monitored_user_id in monitored_user_ids:
                            if monitored_user_id in ignore_uuid:
                                continue
                            if monitored_user_id == user_id:
                                continue
                            if (monitored_user := proxy.end_user.get(monitored_user_id)) is None:
                                continue
                            # create nodes and edges
                            # user-phone-blfdnp-dn-monitored phone-monitored user
                            un = self.user_node_by_id(uid=user_id, proxy=proxy)
                            mun = self.user_node(monitored_user)
                            if only_new_relations:
                                connected = self.connected_user_nodes(un)
                                if mun in connected:
                                    continue
                            pn = self.phone_node(phone)
                            self.add_node(un)
                            self.add_node(pn)
                            self.add_edge(un, pn)
                            blfn = f'blf {blf_dnp}'
                            self.add_node(blfn)
                            self.add_edge(pn, blfn)
                            dn_node = f'dn {blf_dnp}'
                            self.add_node(dn_node)
                            self.add_edge(blfn, dn_node)
                            mpn = self.phone_node(monitored_phone)
                            self.add_node(mpn)
                            self.add_edge(dn_node, mpn)

                            self.add_node(mun)
                            self.add_edge(mpn, mun)
                            users_added += 1
                        # for
                    # for
                # for
            # for
        # for
        return users_added

    def related_users_cpg(self, proxy: Proxy, only_new_relations=False) -> int:
        """
        Identify users related via call pickup groups on lines of any of the users' phones
        :param proxy: CSV proxy
        :param only_new_relations: only a add user relations for users not already in the graph as related
        :return: number of users added to the graph
        """
        print('related users based on call pickup groups...')
        by_cpg = proxy.phones.by_call_pickup_group
        users_added = set()
        related_users_count = 0
        ignore_uid = self.ignore_uid(proxy)
        for cpg_name, phones in by_cpg.items():
            # users related via this cpg is the union of all users of all phones related to this cpg
            user_set = sorted(set(chain.from_iterable(phone.user_set
                                                      for phone in phones)))
            if len(user_set) < 2:
                # nothing to do if not at least two users are involved
                continue
            # for each user create edge: user-phone-cpg
            cpg_node = self.cpg_node(cpg_name)
            for phone in phones:
                phone_node = self.phone_node(phone)
                for user in phone.user_set:
                    if user in ignore_uid:
                        continue
                    if user in users_added:
                        continue
                    self.add_path(self.user_node(user), phone_node, cpg_node)
                    related_users_count += 1
                # for
            # for
        # for
        return related_users_count

    def related_user_sets(self) -> Generator[Set[str], None, None]:
        """
        Generator yielding sets of related user nodes
        :return:
        """
        for connected in nx.connected_components(self):
            yield set(node for node in connected if node.startswith('user '))

    def related_users_by_len(self) -> Dict[int, List[Set[str]]]:
        """
        Cluster sets of related user nodes by size of the sets
        :return:
        """
        r = defaultdict(list)
        for related in self.related_user_sets():
            r[len(related)].append(related)
        return r

    def simplify(self):
        """
        Try to simplify the graph
        :return: None
        """
        log.debug(f'{len(self.nodes)} nodes before cleanup')
        nodes = list(self.nodes())
        removed_nodes = set()
        for node in nodes:
            if node in removed_nodes:
                # already gone
                continue
            connected = nx.node_connected_component(self, node)
            connected_users = [c for c in connected if c.startswith('user ')]
            if len(connected_users) < 2:
                # everything can go
                log.debug(f'removing nodes: {", ".join(connected)}')
                for c in connected:
                    self.remove_node(c)
                    removed_nodes.add(c)
                # for
            # if
        # for
        # remove all non-user nodes at the edges
        while True:
            nodes = [n for n in self.nodes if not n.startswith('user ')]
            deleted_nodes = 0
            for node in nodes:
                if len(list(nx.neighbors(self, node))) == 1:
                    self.remove_node(node)
                    deleted_nodes += 1
            if deleted_nodes:
                log.debug(f'{deleted_nodes} edge nodes deleted')
                continue
            break
        log.debug(f'{len(self.nodes)} nodes after cleanup')

    def draw(self):
        """
        Draw the graph
        :return:
        """

        pos = nx.spring_layout(self, iterations=60)
        # pos = nx.kamada_kawai_layout(self)
        # pos = nx.spiral_layout(self)
        # pos = nx.circular_layout(self)
        # -pos = nx.bipartite_layout(self)
        # -pos = nx.shell_layout(self)
        edge_x = []
        edge_y = []
        for edge in self.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.append(x0)
            edge_x.append(x1)
            edge_x.append(None)
            edge_y.append(y0)
            edge_y.append(y1)
            edge_y.append(None)

        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=0.5, color='#888'),
            hoverinfo='none',
            mode='lines')

        node_x = []
        node_y = []
        hovertext = []

        node_types = sorted(set(n.split()[0] for n in self.nodes()))
        node_colors = {t: c for c, t in enumerate(node_types)}

        for node in self.nodes():
            # x, y = g.nodes[node]['pos']
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            hovertext.append(node)

        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers',
            hoverinfo='text',
            marker=dict(
                showscale=True,
                # colorscale options
                # 'Greys' | 'YlGnBu' | 'Greens' | 'YlOrRd' | 'Bluered' | 'RdBu' |
                # 'Reds' | 'Blues' | 'Picnic' | 'Rainbow' | 'Portland' | 'Jet' |
                # 'Hot' | 'Blackbody' | 'Earth' | 'Electric' | 'Viridis' |
                colorscale='YlGnBu',
                reversescale=True,
                color=[],
                size=10,
                line_width=2))
        node_trace.text = list(self.nodes())
        node_trace.marker.color = [node_colors[n.split()[0]] for n in self.nodes()]

        # noinspection PyTypeChecker
        fig = go.Figure(data=[edge_trace, node_trace],
                        layout=go.Layout(
                            title='User groups',
                            titlefont_size=16,
                            showlegend=False,
                            hovermode='closest',
                            margin=dict(b=20, l=5, r=5, t=40),
                            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                        )
        fig.write_html('user dependencies.html')
        fig.show()

    def draw3d(self):
        """
        Draw the graph in 3d
        :return:
        """
        nodes = []
        node_groups = {}
        for node in self.nodes:
            node_group = node.split()[0]
            if (node_group_id:=node_groups.get(node_group)) is None:
                node_group_id = len(node_group)
                node_groups[node_group_id] = node_group
            nodes.append(GDataNode(id=node, name=node, group=str(node_group_id)))
        links = [GDataLink(source=source, target=target) for source, target in self.edges]
        g_data = GData(nodes=nodes, links=links)
        html_file = 'user dependencies 3d.html'
        with open(html_file, mode='w') as f:
            f.write(JS_TEMPLATE_3D.replace('{}', g_data.model_dump_json(indent=2)))
        webbrowser.open(f'file://{os.path.abspath(html_file)}', new=2)  # nosec:'html_file, new=2)
