from mininet.net import Mininet
from mininet.node import Controller, RemoteController
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel, info
import time

def bso():
    # Initialize the Mininet
    net = Mininet(controller=RemoteController, link=TCLink)

    node_num = 14  # Number of switches and hosts

    # Add switches
    switches = {}
    for i in range(1, node_num + 1):
        switches[i] = net.addSwitch(f's{i}')

    # Add hosts
    hosts = {}
    for i in range(1, node_num + 1):
        ip = f'10.0.0.{i}'
        mac = f'00:00:00:00:01:{i:02d}'  # Ensures MAC has 2 digits for compatibility
        hosts[i] = net.addHost(f'h{i}', ip=ip, mac=mac)

    # Link hosts to their respective switches
    info("*** Creating host-switch links\n")
    for i in range(1, node_num + 1):
        net.addLink(hosts[i], switches[i])

    # Link switches based on the predefined topology
    info("*** Creating switch-switch links\n")
    link_from = [1, 2, 2, 2, 2, 2, 3, 3, 5, 7, 8, 8, 9, 9, 10, 11, 12, 13]
    link_to = [2, 3, 4, 5, 7, 8, 4, 5, 6, 9, 9, 12, 10, 13, 11, 13, 13, 14]

    for lf, lt in zip(link_from, link_to):
        net.addLink(switches[lf], switches[lt])

    # Add a remote controller
    c0 = net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)

    # Start the network
    info("*** Starting the network\n")
    net.start()

    # Wait for the controller to update paths in the network
    info("*** Waiting for controller to update paths\n")
    time.sleep(10)

    # Run the traffic generator script
    info("*** Running traffic generation script\n")
    #CLI(net, script='traffic-gen-script1.sh')

    # Open CLI for manual commands
    CLI(net)

    # Display all hosts for verification
    info("*** Hosts in the network:\n")
    for host in net.hosts:
        info(f"{host}\n")

    # Stop the network
    info("*** Stopping the network\n")
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')  # Set log level to display Mininet information
    bso()

