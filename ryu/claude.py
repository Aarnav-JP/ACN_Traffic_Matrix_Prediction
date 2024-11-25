from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.topology import event, switches
from ryu.topology.api import get_switch, get_link
from ryu.lib import hub

class BasicSpanningTreeDiscovery(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {
        # Use the actual topology switches app
        'switches': switches.Switches
    }

    def __init__(self, *args, **kwargs):
        super(BasicSpanningTreeDiscovery, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.no_flood_ports = set()
        self.hold_down_time = 30
        self.is_active = True
        
        # Create a thread to periodically check and update topology
        self.topology_thread = hub.spawn(self._monitor_topology)

    def _monitor_topology(self):
        """
        Periodically monitor and print topology information
        """
        while self.is_active:
            try:
                switches = get_switch(self)
                links = get_link(self)
                
                self.logger.info(f"Discovered Switches: {len(switches)}")
                self.logger.info(f"Discovered Links: {len(links)}")
                
                for switch in switches:
                    self.logger.info(f"Switch DPID: {switch.dp.id}")
                
                for link in links:
                    self.logger.info(f"Link: {link.src.dpid}:{link.src.port_no} -> {link.dst.dpid}:{link.dst.port_no}")
            except Exception as e:
                self.logger.error(f"Topology monitoring error: {e}")
            
            hub.sleep(10)

    @set_ev_cls(event.EventSwitchEnter)
    def switch_enter_handler(self, ev):
        """
        Handler for when a new switch enters the network
        """
        switch = ev.switch
        self.logger.info(f"Switch entered: {switch.dp.id}")

    @set_ev_cls(event.EventLinkAdd)
    def link_add_handler(self, ev):
        """
        Handler for when a new link is discovered
        """
        link = ev.link
        self.logger.info(f"Link discovered: {link.src.dpid}:{link.src.port_no} -> {link.dst.dpid}:{link.dst.port_no}")

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Install a default flow to send unmatched packets to the controller
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth_pkt = pkt.get_protocol(ethernet.ethernet)

        # Ignore LLDP packets
        if eth_pkt.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        dst = eth_pkt.dst
        src = eth_pkt.src

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        # Learn MAC address
        self.mac_to_port[dpid][src] = in_port

        # Determine output port
        out_port = self.get_out_port(datapath, dst)

        actions = [parser.OFPActionOutput(out_port)]

        # Install a flow if we know the output port
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions, msg.buffer_id)
            else:
                self.add_flow(datapath, 1, match, actions)

        # Send packet out
        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=msg.data if msg.buffer_id == ofproto.OFP_NO_BUFFER else None
        )
        datapath.send_msg(out)

    def get_out_port(self, datapath, dst):
        """
        Determine output port considering spanning tree and no-flood rules
        """
        dpid = datapath.id
        ofproto = datapath.ofproto

        # If destination is known
        if dst in self.mac_to_port.get(dpid, {}):
            port = self.mac_to_port[dpid][dst]
            # Check if this port is not in no-flood list
            if port not in self.no_flood_ports:
                return port

        # Default to flooding if no specific port is found
        return ofproto.OFPP_FLOOD

    def close(self):
        """
        Clean up resources when the application is closed
        """
        self.is_active = False
        if self.topology_thread:
            hub.kill(self.topology_thread)
        super(BasicSpanningTreeDiscovery, self).close()