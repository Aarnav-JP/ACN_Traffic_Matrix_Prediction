#!/bin/bash

# Perform a network-wide ping to verify connectivity
pingall

# Replay traffic for each host
for file in prepared-pcaps/h1/*.pcap; do
    tcpreplay --loop=5000 --loopdelay-ms=1000 -i h1-eth0 --pps=10 $file &
done

for file in prepared-pcaps/h2/*.pcap; do
    tcpreplay --loop=5000 --loopdelay-ms=1000 -i h2-eth0 --pps=8 $file &
done

for file in prepared-pcaps/h3/*.pcap; do
    tcpreplay --loop=5000 --loopdelay-ms=1000 -i h3-eth0 --pps=5 $file &
done

for file in prepared-pcaps/h4/*.pcap; do
    tcpreplay --loop=5000 --loopdelay-ms=1000 -i h4-eth0 --pps=12 $file &
done

for file in prepared-pcaps/h5/*.pcap; do
    tcpreplay --loop=5000 --loopdelay-ms=1000 -i h5-eth0 --pps=11 $file &
done

for file in prepared-pcaps/h6/*.pcap; do
    tcpreplay --loop=5000 --loopdelay-ms=1000 -i h6-eth0 --pps=15 $file &
done

for file in prepared-pcaps/h7/*.pcap; do
    tcpreplay --loop=5000 --loopdelay-ms=1000 -i h7-eth0 --pps=6 $file &
done

for file in prepared-pcaps/h8/*.pcap; do
    tcpreplay --loop=5000 --loopdelay-ms=1000 -i h8-eth0 --pps=9 $file &
done

for file in prepared-pcaps/h9/*.pcap; do
    tcpreplay --loop=5000 --loopdelay-ms=1000 -i h9-eth0 --pps=13 $file &
done

for file in prepared-pcaps/h10/*.pcap; do
    tcpreplay --loop=5000 --loopdelay-ms=1000 -i h10-eth0 --pps=14 $file &
done

for file in prepared-pcaps/h11/*.pcap; do
    tcpreplay --loop=5000 --loopdelay-ms=1000 -i h11-eth0 --pps=14 $file &
done

for file in prepared-pcaps/h12/*.pcap; do
    tcpreplay --loop=5000 --loopdelay-ms=1000 -i h12-eth0 --pps=16 $file &
done

for file in prepared-pcaps/h13/*.pcap; do
    tcpreplay --loop=5000 --loopdelay-ms=1000 -i h13-eth0 --pps=8 $file &
done

for file in prepared-pcaps/h14/*.pcap; do
    tcpreplay --loop=5000 --loopdelay-ms=1000 -i h14-eth0 --pps=7 $file &
done
