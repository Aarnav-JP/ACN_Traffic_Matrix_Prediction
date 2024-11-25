from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib.packet import packet, ethernet, lldp
from ryu.ofproto import ofproto_v1_3
from ryu.lib import networkx as nx
import time

class SpanningTreeController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SpanningTreeController, self).__init__(*args, **kwargs)
        self.datapaths = {}  # Store connected switches (DPIDs)
        self.mac_to_port = {}  # MAC to port mapping
        self.topology = nx.Graph()  # Topology graph
        self.last_update_time = time.time()
        self.hold_down = 15  # Hold-down time in seconds

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def _switch_features_handler(self, ev):
        # Add the switch to the datapaths dictionary
        datapath = ev.msg.datapath
        self.datapaths[datapath.id] = datapath
        self.mac_to_port[datapath.id] = {}

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        packet_in = ev.msg
        datapath = ev.msg.datapath
        in_port = packet_in.in_port
        packet_data = ev.msg.data
        pkt = packet.Packet(packet_data)

        # Get the Ethernet frame and check if it's an LLDP packet
        eth_pkt = pkt.get_protocol(ethernet.ethernet)
        if eth_pkt:
            if eth_pkt.ethertype == ethernet.ETH_TYPE_LLDP:
                self._learn_topology(datapath, packet_in, pkt)
                return

        # If it's not an LLDP or unknown destination, drop packet or install flow
        self._handle_packet(datapath, in_port, pkt)

    def _learn_topology(self, datapath, packet_in, pkt):
        # Parse the LLDP packet to learn topology (neighbors)
        lldp_pkt = pkt.get_protocol(lldp.lldp)
        for p in lldp_pkt:
            # Extract information from the LLDP
            src_dpid = datapath.id
            dst_dpid = p.chassis_id
            src_port = packet_in.in_port

            # Add the link to the topology graph
            self.topology.add_edge(src_dpid, dst_dpid, port=src_port)
            self.topology.add_edge(dst_dpid, src_dpid, port=p.port_id)

            self.logger.info("Learned link: %s <-> %s (Port: %s)", src_dpid, dst_dpid, src_port)

        self._compute_spanning_tree()

    def _compute_spanning_tree(self):
        # Compute the minimum spanning tree using NetworkX
        mst = nx.minimum_spanning_tree(self.topology)
        self.logger.info("Spanning Tree Computed: %s", mst.edges)

        # Disable ports that are not part of the spanning tree
        for link in self.topology.edges:
            if link not in mst.edges:
                src, dst = link
                port = self.topology[src][dst]['port']
                self._disable_port(src, port)

    def _disable_port(self, dpid, port):
        # Send a flow-mod to disable the port (drop packets on this port)
        datapath = self.datapaths.get(dpid)
        if datapath:
            ofproto = datapath.ofproto
            parser = datapath.ofproto_parser
            match = parser.OFPMatch(in_port=port)
            actions = []
            mod = parser.OFPFlowMod(datapath=datapath, priority=1, match=match, actions=actions)
            datapath.send_msg(mod)
            self.logger.info("Disabled port %s on switch %s", port, dpid)

    def _handle_packet(self, datapath, in_port, pkt):
        # Handle non-LLDP or unknown destination packets
        eth_pkt = pkt.get_protocol(ethernet.ethernet)
        if eth_pkt:
            dst_mac = eth_pkt.dst
            src_mac = eth_pkt.src
            self.mac_to_port[datapath.id][src_mac] = in_port

            # Drop if it's a multicast packet (flooding)
            if dst_mac == 'ff:ff:ff:ff:ff:ff':
                self._drop_packet(datapath, in_port)
                return

            # If destination MAC is known, forward the packet
            if dst_mac in self.mac_to_port[datapath.id]:
                out_port = self.mac_to_port[datapath.id][dst_mac]
                self._forward_packet(datapath, in_port, out_port, pkt)
            else:
                # If destination is unknown, drop packet or install flood rule
                self._drop_packet(datapath, in_port)

    def _forward_packet(self, datapath, in_port, out_port, pkt):
        # Forward the packet to the destination port
        parser = datapath.ofproto_parser
        actions = [parser.OFPActionOutput(out_port)]
        data = pkt.data
        out_msg = parser.OFPPacketOut(datapath=datapath, in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out_msg)

    def _drop_packet(self, datapath, in_port):
        # Send a flow-mod to drop the packet
        parser = datapath.ofproto_parser
        match = parser.OFPMatch(in_port=in_port)
        actions = []
        drop_msg = parser.OFPFlowMod(datapath=datapath, priority=1, match=match, actions=actions, command=ofproto_v1_3.OFPFC_DELETE)
        datapath.send_msg(drop_msg)

    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def _port_status_handler(self, ev):
        # Handle port status updates
        pass

    def _enable_hold_down(self):
        # Implement the hold-down timer to delay updates for a set duration
        now = time.time()
        if now - self.last_update_time < self.hold_down:
            self.logger.info("Hold-down active, skipping updates.")
            return
        self.last_update_time = now
        self.logger.info("Hold-down timer expired, allowing updates.")
