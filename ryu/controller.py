from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib.packet import packet, ethernet
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub
import numpy as np
import os
import csv
from copy import deepcopy
from datetime import datetime

class CombinedApp(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(CombinedApp, self).__init__(*args, **kwargs)
        
        # Read the output file path from an environment variable
        self.output = os.getenv('OUTPUT_FILE', None)

        # Log the output file path for debugging
        if self.output:
            self.logger.info(f"Output file set to: {self.output}")

            # If the file doesn't exist, create it
            if not os.path.isfile(self.output):
                with open(self.output, 'w') as f:
                    f.write("Timestamp," + ",".join([f"Node{i+1}" for i in range(14)]) + "\n")
        else:
            self.logger.warning("No output file specified. Traffic data will not be saved.")

        # Initialize other attributes for traffic observation
        self.node_num = 7  # Number of nodes
        self.interval = 60  # Interval in seconds for traffic matrix calculation
        self.latest_traffic = np.zeros((self.node_num, self.node_num), dtype=object)
        self.previous_traffic = np.zeros((self.node_num, self.node_num), dtype=object)
        
        # Start monitoring threads
        self.monitor_thread = hub.spawn(self._monitor)
        self.tm_thread = hub.spawn(self._traffic_monitor)

        # Datapath-related attributes for handling switch connections
        self.datapaths = {}
        self.mac_to_port = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)
        self.add_topology_flow_rules(datapath)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority, match=match, instructions=inst, buffer_id=buffer_id)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority, match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, CONFIG_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            self.datapaths[datapath.id] = datapath
        elif ev.state == CONFIG_DISPATCHER:
            self.datapaths.pop(datapath.id, None)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        # Ignore LLDP packets
        if eth.ethertype == 0x88cc:
            return

        dpid = datapath.id
        in_port = msg.match['in_port']

        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][eth.src] = in_port

        if eth.dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][eth.dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=eth.dst, eth_src=eth.src)
            self.add_flow(datapath, 1, match, actions)

        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id, in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)

    def add_topology_flow_rules(self, datapath):
        """
        Add topology-specific flow rules to switches based on the topology.
        """
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id  # Switch ID

        # Topology: Add forwarding rules for inter-switch connections
        if dpid == 1:
            # Switch 1 rules
            self.add_flow(datapath, 1, parser.OFPMatch(eth_dst="00:00:00:00:00:02"), [parser.OFPActionOutput(2)])
            self.add_flow(datapath, 1, parser.OFPMatch(eth_dst="00:00:00:00:00:03"), [parser.OFPActionOutput(3)])
        elif dpid == 2:
            # Switch 2 rules
            self.add_flow(datapath, 1, parser.OFPMatch(eth_dst="00:00:00:00:00:01"), [parser.OFPActionOutput(1)])
            self.add_flow(datapath, 1, parser.OFPMatch(eth_dst="00:00:00:00:00:04"), [parser.OFPActionOutput(3)])
        elif dpid == 3:
            # Switch 3 rules
            self.add_flow(datapath, 1, parser.OFPMatch(eth_dst="00:00:00:00:00:02"), [parser.OFPActionOutput(1)])
            self.add_flow(datapath, 1, parser.OFPMatch(eth_dst="00:00:00:00:00:05"), [parser.OFPActionOutput(3)])
        elif dpid == 4:
            # Switch 4 rules
            self.add_flow(datapath, 1, parser.OFPMatch(eth_dst="00:00:00:00:00:03"), [parser.OFPActionOutput(1)])
            self.add_flow(datapath, 1, parser.OFPMatch(eth_dst="00:00:00:00:00:06"), [parser.OFPActionOutput(3)])
        elif dpid == 5:
            # Switch 5 rules
            self.add_flow(datapath, 1, parser.OFPMatch(eth_dst="00:00:00:00:00:04"), [parser.OFPActionOutput(1)])
            self.add_flow(datapath, 1, parser.OFPMatch(eth_dst="00:00:00:00:00:07"), [parser.OFPActionOutput(3)])
        elif dpid == 6:
            # Switch 6 rules
            self.add_flow(datapath, 1, parser.OFPMatch(eth_dst="00:00:00:00:00:05"), [parser.OFPActionOutput(1)])
            self.add_flow(datapath, 1, parser.OFPMatch(eth_dst="00:00:00:00:00:01"), [parser.OFPActionOutput(3)])
        elif dpid == 7:
            # Switch 7 rules
            self.add_flow(datapath, 1, parser.OFPMatch(eth_dst="00:00:00:00:00:06"), [parser.OFPActionOutput(1)])
            self.add_flow(datapath, 1, parser.OFPMatch(eth_dst="00:00:00:00:00:02"), [parser.OFPActionOutput(3)])


    def _monitor(self):
        while True:
            for dp in self.datapaths.values():
                self._request_stats(dp)
            hub.sleep(self.interval)

    def _request_stats(self, datapath):
        parser = datapath.ofproto_parser
        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):
        body = ev.msg.body
        dpid = ev.msg.datapath.id
        traffic = np.zeros(self.node_num, dtype=object)
        self.logger.info(f"Flow stats received for datapath {dpid}: {body}")

        for stat in body:
            if 'ipv4_src' in stat.match and 'ipv4_dst' in stat.match:
                src_ip = stat.match['ipv4_src']
                dst_ip = stat.match['ipv4_dst']
                src_id = int(stat.match['ipv4_src'].split('.')[-1])
                dst_id = int(stat.match['ipv4_dst'].split('.')[-1])
                self.logger.info(f"Flow from {src_ip} to {dst_ip}, byte count: {stat.byte_count}")

                traffic[dst_id - 1] += stat.byte_count
        self.latest_traffic[dpid - 1] = traffic
        self.logger.info(f"Updated traffic matrix for datapath {dpid}: {traffic}")

    def _traffic_monitor(self):
        self.logger.info("Traffic monitoring thread is running")
        while True:
            hub.sleep(1)
        
        # Calculate the difference in traffic and the traffic matrix
            duration = self.interval
            dif_matrix = self.latest_traffic - self.previous_traffic
            traffic_matrix = dif_matrix / duration
        
            # Log the traffic matrix to confirm it's being calculated
            self.logger.info(f"Calculated traffic matrix:\n{traffic_matrix}")
        
            if self.output:
                self.logger.info(f"Writing traffic matrix to: {self.output}")
                with open(self.output, 'a', newline='') as f:
                    writer = csv.writer(f)
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    row = [timestamp] + traffic_matrix.ravel().tolist()
                    writer.writerow(row)
        
        # Update the previous_traffic matrix for the next iteration
            self.previous_traffic = deepcopy(self.latest_traffic)
  