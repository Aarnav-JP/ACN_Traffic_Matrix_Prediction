from mininet.net import Mininet
from mininet.node import Controller, RemoteController
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel, info

import time

def bso():
    net = Mininet(controller=RemoteController, link=TCLink)

    node_num = 14  # Total number of switches and hosts

    info("*** Creating switches\n")
    switches = []
    for i in range(1, node_num + 1):
        switches.append(net.addSwitch('s%d' % i))

    info("*** Creating hosts\n")
    hosts = []
    for i in range(1, node_num + 1):
        host = net.addHost('h%d' % i,
                           ip='10.0.0.%d' % i,
                           mac='00:00:00:00:01:%02d' % i)
        hosts.append(host)

    info("*** Creating host-switch links\n")
    for i in range(node_num):
        net.addLink(hosts[i], switches[i])

    info("*** Creating switch-switch links\n")
    link_from = [1, 2, 2, 2, 2, 2, 3, 3, 5, 7, 8, 8, 9, 9, 10, 11, 12, 13]
    link_to = [2, 3, 4, 5, 7, 8, 4, 5, 6, 9, 9, 12, 10, 13, 11, 13, 13, 14]

    for lf, lt in zip(link_from, link_to):
        net.addLink(switches[lf - 1], switches[lt - 1])

    info("*** Adding Remote Controller\n")
    c0 = net.addController('c0',
                           controller=RemoteController,
                           ip='127.0.0.1',
                           port=6633)

    info("*** Starting network\n")
    net.start()

    # Allow time for the Ryu controller to push initial flow rules
    info("*** Waiting for controller to initialize paths\n")
    time.sleep(10)

    info("*** Running traffic generation commands\n")
    # Example traffic generation commands
    #net.get('h1').cmd('./traffic-gen-script.sh')
    #CLI(net, script='traffic-gen-script1.sh')


    # Start CLI for interactive testing
    CLI(net)

    info("*** Stopping network\n")
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    bso()

