#!/usr/bin/env python

from mininet.net import Mininet
from mininet.node import Controller, RemoteController, OVSSwitch
from mininet.link import TCLink
from mininet.log import setLogLevel, info
from mininet.cli import CLI
import os

def customTopology():
    # Create the Mininet network
    net = Mininet(controller=RemoteController, switch=OVSSwitch, link=TCLink)

    info('*** Adding controller\n')
    controller = net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6653)

    info('*** Adding switches\n')
    switches = []
    for i in range(1, 8):  # 7 switches
        switch = net.addSwitch(f's{i}')
        switches.append(switch)

    info('*** Adding hosts\n')
    hosts = []
    for i in range(1, 8):  # 7 hosts
        host = net.addHost(f'h{i}', ip=f'10.0.0.{i}')
        hosts.append(host)

    info('*** Creating links between switches and hosts\n')
    for i in range(7):
        net.addLink(switches[i], hosts[i])  # Connect each host to a switch

    info('*** Creating links between switches\n')
    for i in range(6):  # Connect switches linearly
        net.addLink(switches[i], switches[i + 1])

    info('*** Starting network\n')
    net.build()
    controller.start()
    for switch in switches:
        switch.start([controller])

    info('*** Starting traffic generation\n')

    # Base directory for the PCAP files
    base_dir = "/home/sanskar/Project/prepared-pcaps/"

    hosts[0].cmd('xterm -e bash &')
    hosts[1].cmd('xterm -e bash &')


    # Iterate through each host and replay traffic
    for i, src_host in enumerate(hosts, 1):  # Source host (h1, h2, ...)
        host_dir = os.path.join(base_dir, f"h{i}")  # Directory for the host's PCAP files

        if not os.path.exists(host_dir):
            info(f"Directory {host_dir} not found. Skipping h{i}.\n")
            continue

        for pcap_file in os.listdir(host_dir):  # Iterate over all PCAP files in the host directory
            if pcap_file.endswith(".pcap"):
                # Extract the destination host from the filename
                dest_host_id = os.path.splitext(pcap_file)[0]  # Filename without extension (e.g., "2" for "2.pcap")
                try:
                    dest_host = hosts[int(dest_host_id) - 1]  # Convert to zero-indexed host ID
                except (ValueError, IndexError):
                    info(f"Invalid destination host in file: {pcap_file}. Skipping.\n")
                    continue

                pcap_path = os.path.join(host_dir, pcap_file)

                # Replay traffic using the PCAP file
                info(f"Replaying traffic on h{i} to h{dest_host_id} using {pcap_file}\n")
                command = f"tcpreplay --loop=5000 --loopdelay-ms=1000 -i h{i}-eth0 --pps=10 {pcap_path} &"
                src_host.cmd(command)

    info('*** Running CLI\n')
    CLI(net)

    info('*** Stopping network\n')
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    customTopology()



    