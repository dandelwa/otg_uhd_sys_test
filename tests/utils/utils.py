
import time
import re
import ipaddr
from lxml.builder import unicode
from netaddr import IPNetwork
from ipaddress import IPv6Network, IPv6Address
from random import getrandbits
import sys

class verify :
    def __init__(self, api, protocol= "BGP"):
        self.stats = open("stats.log", "+a")
        self.info = open("info.log", "+a")
        self.api = api
        self.protocol = protocol


    def __del__(self):
        self.stats.close()
        self.info.close()

    def followSessionsOverTime(self, noofdevices, timeout = 300):
        sessions = noofdevices
        startTime = time.perf_counter()
        self.stats.write("%s\n\nNew Log:\n" % (str(startTime)))
        self.info.write("\n\nNew Log:\n")
        while True:
            metrics_request = self.api.metrics_request()
            if self.protocol == "ISIS":
                metrics_request.isis.router_names = []
                resp = self.api.get_metrics(metrics_request)
                isis = resp.isis_metrics
                up_list = 0
                down_list = 0
                for obj in isis:
                    self.stats.write("%s : %d\n" % (obj.name, obj.l1_sessions_up))
                    if obj.l1_sessions_up == 1:
                        up_list +=1
                    else:
                        down_list +=1
                print("u %d : d %d " % (up_list, down_list))
                self.info.write("u %d : d %d \n" % (up_list, down_list))
                endTime = time.perf_counter()
                if (endTime - startTime) > timeout:
                    assert sessions == up_list
                    break
            elif self.protocol == "BGP":
                metrics_request.bgpv4.peer_names = []
                resp = self.api.get_metrics(metrics_request)
                bgp = resp.bgpv4_metrics
                up_list = 0
                down_list = 0
                for obj in bgp:
                    self.stats.write("%s : %s\n" % (obj.name, obj.session_state))
                    if obj.session_state == "up":
                        up_list +=1
                    else:
                        down_list +=1
                print("u %d : d %d " % (up_list, down_list))
                self.info.write("u %d : d %d \n" % (up_list, down_list))
                endTime = time.perf_counter()
                if (endTime - startTime) > timeout:
                    assert sessions == up_list
                    break

    def verifyTransmission(self, noofpackets, timeout = 300):
        trial = 0
        startTime = time.perf_counter()
        metrics_request = self.api.metrics_request()
        metrics_request.flow.flow_names = []
        while trial < 100:
            endTime = time.perf_counter()
            if endTime - startTime > timeout:
                return 100
            metrics_response = self.api.get_metrics(metrics_request)
            metrics = metrics_response.flow_metrics
            counter = 0
            for i in range(0, len(metrics)):
                metric = metrics[i]
                self.stats.write("name : %s  tx : %d  rx: %d\n" % (metric.name, metric.frames_tx ,metric.frames_rx))
                if metric.frames_tx == noofpackets:
                    if metric.frames_rx == noofpackets:
                        counter += 1
            if counter == len(metrics):
                return trial
            trial += 1
        return trial




# class ConfigValues:
#     def __init__(self, num_of_devices, num_of_routes, number_of_flows):
#         self.num_of_devices = num_of_devices
#         self.num_of_routes = num_of_routes
#         self.number_of_flows = number_of_flows

#     def get_macs()
def get_macs(mac, count, offset=1):
    """
    Take mac as start mac returns the count of macs in a list
    """
    mac_list = list()
    for i in range(count):
        mac_address = "{:012X}".format(int(mac, 16) + offset * i)
        mac_address = ":".join(
            format(s, "02x") for s in bytearray.fromhex(mac_address)
        )
        mac_list.append(mac_address)
    return mac_list


def get_ip_addresses(ip, count):
    """
    Take ip as start ip returns the count of ips in a list
    """
    ip_list = list()
    for i in range(count):
        ipv4address = ipaddr.IPv4Address(ip)
        ipv4address = ipv4address + i
        value = ipv4address._string_from_ip_int(ipv4address._ip)
        ip_list.append(value)
    return ip_list


def get_ipv6_addrs(ip, count):
    """
    Get N IPv6 addresses in a subnet.
    Args:
        subnet (str): IPv6 subnet, e.g., '2001::1/64'
        number_of_ip (int): Number of IP addresses to get
    Return:
        Return n IPv6 addresses in this subnet in a list.
    """
    subnet = str(IPNetwork(ip).network) + "/" + str(ip.split("/")[1])
    if sys.version_info[0] == 2:
        subnet = unicode(subnet, "utf-8")
    ipv6_list = []
    for i in range(count):
        network = IPv6Network(subnet)
        address = IPv6Address(
            network.network_address
            + getrandbits(network.max_prefixlen - network.prefixlen)
        )
        ipv6_list.append(str(address))

    return ipv6_list


def stats_ok(api, packets, utils):
    """
    Returns true if stats are as expected, false otherwise.
    """
    _, flow_stats = utils.get_all_stats(api)

    flow_rx = sum([f.frames_rx for f in flow_stats])
    return flow_rx == packets


def wait_for_metrics(api, metrics_request, attribute_pairs):
    request = f"Wait for metrics:{metrics_request.choice} "
    for attribute_pair in attribute_pairs:
        request += f"{attribute_pair[0]}={attribute_pair[1]} "
    print(request)
    trial = 1
    count = 0
    while trial != 100:
        metrics_response = api.get_metrics(metrics_request)
        if metrics_response.choice == "port_metrics":
            metrics = metrics_response.port_metrics
        elif metrics_request.choice == "bgpv4":
            metrics = metrics_response.bgpv4_metrics
        elif metrics_request.choice == "bgpv6":
            metrics = metrics_response.bgpv6_metrics
        elif metrics_request.choice == "isis":
            metrics = metrics_response.isis_metrics
        elif metrics_request.choice == "flow":
            metrics = metrics_response.flow_metrics
        elif metrics_request.choice == "lag":
            metrics = metrics_response.lag_metrics
        elif metrics_request.choice == "rsvp":
            metrics = metrics_response.rsvp_metrics
        if len(metrics) == 0:
            continue
        expected = 0
        actual = 0
        for attribute_pair in attribute_pairs:
            expected += attribute_pair[1]
            for metric in metrics:
                actual += getattr(metric, attribute_pair[0], 0)
        if metrics_request.choice == "flow":
            count = 0
            for i in range(1, len(metrics)):
                metric = metrics[i]
                row = f"{metric.name} {metric.frames_tx} {metric.frames_rx} "
                if metric.frames_tx == metric.frames_rx:
                    count +=1
                for metric_group in metric.metric_groups:
                    row += f"{metric_group.name}={metric_group.value} "
                print(f"row:{i} {row}")
        if count >= 7:
            return trial
        trial += 1
    return trial

def getPortsFromBinding(filename="/home/test/remote/test_folder/systemTests/config/ports.config"):
    repetitions = {}
    port_list = ["rustic1-tf2-qa1","rustic2-tf2-qa1","rustic3-tf2-qa1","rustic4-tf2-qa1","rustic5-tf2-qa1","rustic6-tf2-qa1",
                 "rustic7-tf2-qa1","rustic8-tf2-qa1","rustic9-tf2-qa1","rustic10-tf2-qa1","rustic11-tf2-qa1","rustic12-tf2-qa1",
                 "rustic13-tf2-qa1","rustic14-tf2-qa1","rustic15-tf2-qa1","rustic16-tf2-qa1"]
    

    with open(filename, 'r') as file:
        for line in file:
            for ports in port_list:
                if ports in line:
                    index = port_list.index(ports)
                    port = file.readline()
                    repetitions[index+1] = port.strip("name: ").strip("\n").strip('"')

    return(repetitions)


        

    
    

    


        
