import pytest
import snappi
from utils.utils import *

def pytest_addoption(parser):
    parser.addoption(
        '--controller', action='store', default='obox0.lbj.is.keysight.com:40051', help='Mention IP:GRPC_PORT wrt to controller'
    )
    parser.addoption(
        '--noofdevices', action='store', default=100, help='Mention the number of devices per port to be configured'
    )
    parser.addoption(
        '--noofroutes', action='store', default=10, help='Mention the number of routes per device'
    )
    parser.addoption(
        '--noofflows', action='store', default=8, help='Mention the number of traffic flows. Max 16 as of now.'
    )
    parser.addoption(
        '--noofports', action='store', default=2, help='Mention the number of ports to be used to configure the following. options are 2, 4, 6 and 8'
    )
    parser.addoption(
        '--noofpkts', action='store', default=100, help='Mention the number of packets to be transmitted per flow.'
    )
    parser.addoption(
        '--framesize', action='store', default=64, help='Mention the frame size. '
    )
    parser.addoption(
        '--sessiontimeout', action='store', default=180, help='Controller will be polled for session stats for the said timeout, post which we check if all the sessions have been attained and retained. '
    )
    
@pytest.fixture
def command_line_args(request):
    args = {}
    args['controller'] = request.config.getoption('--controller')
    portList = getPortsFromBinding()
    numberofdevices = int(request.config.getoption('--noofdevices'))
    noofroutes = int(request.config.getoption('--noofroutes'))
    noofflows = int(request.config.getoption('--noofflows'))
    noofports = int(request.config.getoption('--noofports'))
    packets = int(request.config.getoption('--noofpkts'))
    size = int(request.config.getoption('--framesize'))
    timeout = int(request.config.getoption('--sessiontimeout'))

    if int(noofflows) > 16:
        print("Adjusting no of flows to 16.")
        noofflows = 16
    if noofports not in [2,4,6,8,10,12,14,16]:
        print("No of ports provided are not in the allowed list of 2,4,6, 8 upto 16")
        raise ValueError('No of ports not in 2,4,6,8,10,12,14,16')
    
    args['noofdevices'] = numberofdevices
    args['noofflows'] = noofflows
    args['noofports'] = noofports
    args['noofroutes'] = noofroutes
    args['packets'] = packets
    args['size'] = size
    args['ports'] = portList
    args['timeout'] = timeout
    
    return args

@pytest.fixture(scope='function')
def connect(command_line_args):
    args = command_line_args
    api = snappi.api(location=command_line_args['controller'], transport="grpc", verify=False, version_check=False)
    api.request_timeout = 180
    args['api'] = api
    return args

@pytest.fixture(scope='function')
def config_n_port_b2b_bgp(connect):
    api = connect['api']
    noofports = connect['noofports']
    noofdevices=connect['noofdevices']
    noofflows=connect['noofflows']
    ports = connect['ports']
    packets = connect['packets']
    size= connect['size']
    config = api.config()
    l1 = config.layer1.layer1()[0]
    l1.name = "l1"
    l1.speed = "speed_400_gbps"
    config_values = {}
    macs = get_macs("000000000011", 2 * noofdevices)
    config_values["tx_macs"], config_values["rx_macs"] = macs[::2], macs[1::2]
    config_values["vlan_ids"] = [str(i) for i in range(1, noofdevices + 1)]
    ip_adds = get_ip_addresses("10.10.2.1", 2 * noofdevices)
    config_values["tx_adds"], config_values["rx_adds"] = (
        ip_adds[::2],
        ip_adds[1::2],
    )
    n = int(noofports/2)
    l1ports = []
    for iter in range(0,n):
        index1 = iter*2+1
        index2 = iter*2+2
        p1 = ports[index1]
        p2 = ports[index2]

        port1 = config.ports.add(name="port{0}".format(index1), location = p1)
        port2 = config.ports.add(name="port{0}".format(index2), location = p2)
        l1ports.append(port1.name)
        l1ports.append(port2.name)
        tx_ip_list = []
        rx_ip_list = []

        for dev in range(0, noofdevices):
            d1 = config.devices.device(name="{1}d{0}".format(dev+1,index1))[-1]
            e1 = d1.ethernets.ethernet(name="{1}eth{0}".format(dev+1,index1))[-1]
            e1.connection.port_name = port1.name
            e1.mac =  config_values["tx_macs"][dev - 1]
            e1.mtu = 1500
            ip1 = e1.ipv4_addresses.add()
            ip1.name = "{1}ip{0}".format(dev+1,index1)
            tx_ip_list.append(ip1.name)
            ip1.address = config_values["tx_adds"][dev - 1]
            ip1.gateway = config_values["rx_adds"][dev - 1]
            ip1.prefix = 24
            bgp1 = d1.bgp
            bgp1.router_id = config_values["tx_adds"][dev - 1]
            bgp1_int = bgp1.ipv4_interfaces.add()
            bgp1_int.ipv4_name = ip1.name
            peer1 = bgp1_int.peers.add()
            peer1.name = "{1}BGP Peer {0}".format(dev+1,index1)
            peer1.as_type = "ibgp"
            peer1.peer_address = config_values["rx_adds"][dev - 1]
            peer1.as_number = 65200

        for dev in range(0, noofdevices):
            d2 = config.devices.device(name="{1}d_{0}".format(dev+1,index2))[-1]
            e2 = d2.ethernets.ethernet(name="{1}eth_{0}".format(dev+1,index2))[-1]
            e2.connection.port_name = port2.name
            e2.mac =  config_values["rx_macs"][dev - 1]
            e2.mtu = 1500
            ip2 = e2.ipv4_addresses.add()
            ip2.name = "{1}ip_{0}".format(dev+1,index2)
            rx_ip_list.append(ip2.name)
            ip2.address = config_values["rx_adds"][dev - 1]
            ip2.gateway = config_values["tx_adds"][dev - 1]
            ip2.prefix = 24
            bgp2 = d2.bgp
            bgp2.router_id = config_values["rx_adds"][dev - 1]
            bgp2_int = bgp2.ipv4_interfaces.add()
            bgp2_int.ipv4_name = ip2.name
            peer2 = bgp2_int.peers.add()
            peer2.name = "{1}BGP Peer_ {0}".format(dev+1,index2)
            peer2.as_type = "ibgp"
            peer2.peer_address = config_values["tx_adds"][dev - 1]
            peer2.as_number = 65200
    holder = 1
    for flowindex in range(noofflows):
        flow = config.flows.add(name=f"flow {flowindex + 1}")
        flow.tx_rx.device.tx_names = [tx_ip_list[flowindex]]
        flow.tx_rx.device.rx_names = [rx_ip_list[flowindex]]
        holder += 1
        if holder > noofdevices:
            holder = 1
        flow.size.fixed = size
        flow.duration.fixed_packets.packets = packets
        flow.metrics.enable = True

    l1.port_names = l1ports
    
    response = api.set_config(config)
    connect['set_response'] = response
    return connect

@pytest.fixture(scope='function')
def config_n_port_b2b_isis(connect):
    api = connect['api']
    noofports = connect['noofports']
    noofdevices=connect['noofdevices']
    noofflows=connect['noofflows']
    ports = connect['ports']
    packets = connect['packets']
    size= connect['size']
    noofroutes=connect['noofroutes']
    config = api.config()
    l1 = config.layer1.layer1()[0]
    l1.name = "l1"
    l1.speed = "speed_400_gbps"
    config_values = {}
    macs = get_macs("000000000011", 2 * noofdevices)
    config_values["tx_macs"], config_values["rx_macs"] = macs[::2], macs[1::2]
    config_values["vlan_ids"] = [str(i) for i in range(1, noofdevices + 1)]
    ip_adds = get_ip_addresses("10.10.2.1", 2 * noofdevices)
    if noofdevices > noofflows:
        setval = noofdevices
    else:
        setval = noofflows 
    config_values["tx_rr_add1"] = get_ip_addresses("200.1.0.0", setval)
    config_values["tx_rr_add2"] = get_ip_addresses("201.1.0.0", setval)
    next_hop_addr = get_ip_addresses("4.4.4.1", noofroutes)
    config_values["rx_rr_add1"] = get_ip_addresses("100.1.0.0", setval)
    config_values["rx_rr_add2"] = get_ip_addresses("101.1.0.0", setval)
    config_values["tx_adds"], config_values["rx_adds"] = (
        ip_adds[::2],
        ip_adds[1::2],
    )
    n = int(noofports/2)
    l1ports = []
    for iter in range(0,n):
        index1 = iter*2+1
        index2 = iter*2+2
        p1 = ports[index1]
        p2 = ports[index2]

        port1 = config.ports.add(name="port{0}".format(index1), location = p1)
        port2 = config.ports.add(name="port{0}".format(index2), location = p2)
        l1ports.append(port1.name)
        l1ports.append(port2.name)
        tx_ip_list = []
        rx_ip_list = []

        for dev in range(0, noofdevices):
            d1 = config.devices.device(name="{1}d{0}".format(dev+1,index1))[-1]
            e1 = d1.ethernets.ethernet(name="{1}eth{0}".format(dev+1,index1))[-1]
            e1.connection.port_name = port1.name
            e1.mac =  config_values["tx_macs"][dev - 1]
            e1.mtu = 1500
            ip1 = e1.ipv4_addresses.add()
            ip1.name = "{1}ip{0}".format(dev+1,index1)
            tx_ip_list.append(ip1.name)
            ip1.address = config_values["tx_adds"][dev - 1]
            ip1.gateway = config_values["rx_adds"][dev - 1]
            ip1.prefix = 24
            isis1 = d1.isis
            isis1.name = "{1}ISIS{0}".format(dev+1, index1)
            isis1.system_id = "640000000001"
            isis1.basic.ipv4_te_router_id = config_values['tx_adds'][dev - 1]
            isis1.basic.hostname = "{1}ixia-c-port{0}".format(dev+1, index1)
            isis1.advanced.area_addresses = ["490001"]
            isis1.advanced.csnp_interval = 10000
            isis1.advanced.enable_hello_padding = True
            isis1.advanced.lsp_lifetime = 1200
            isis1.advanced.lsp_mgroup_min_trans_interval = 5000
            isis1.advanced.lsp_refresh_rate = 900
            isis1.advanced.max_area_addresses = 3
            isis1.advanced.max_lsp_size = 1492
            isis1.advanced.psnp_interval = 2000
            isis1.advanced.enable_attached_bit = False
            int1 = isis1.interfaces.add(name="{1}isis1int{0}".format(dev+1, index1))
            int1.eth_name = e1.name
            int1.l2_settings.dead_interval = 30
            int1.l2_settings.hello_interval = 10
            int1.l2_settings.priority = 0
            int1.level_type = int1.LEVEL_1
            int1.metric = 10
            rr1 = isis1.v4_routes.add(name="{1}rr{0}".format(dev+1, index1))
            rr1.addresses.add(
                count=noofroutes, address=config_values["rx_rr_add1"][dev - 1], prefix=32
            )
            rr1.link_metric = 10
            rr1.origin_type = rr1.INTERNAL

        for dev in range(0, noofdevices):
            d2 = config.devices.device(name="{1}d_{0}".format(dev+1,index2))[-1]
            e2 = d2.ethernets.ethernet(name="{1}eth_{0}".format(dev+1,index2))[-1]
            e2.connection.port_name = port2.name
            e2.mac =  config_values["rx_macs"][dev - 1]
            e2.mtu = 1500
            ip2 = e2.ipv4_addresses.add()
            ip2.name = "{1}ip_{0}".format(dev+1,index2)
            rx_ip_list.append(ip2.name)
            ip2.address = config_values["rx_adds"][dev - 1]
            ip2.gateway = config_values["tx_adds"][dev - 1]
            ip2.prefix = 24
            isis2 = d2.isis
            isis2.name = "{1}ISIS{0}".format(dev+1, index2)
            isis2.system_id = "640000000001"
            isis2.basic.ipv4_te_router_id = config_values['tx_adds'][dev - 1]
            isis2.basic.hostname = "{1}ixia-c-port{0}".format(dev+1, index2)
            isis2.advanced.area_addresses = ["490001"]
            isis2.advanced.csnp_interval = 10000
            isis2.advanced.enable_hello_padding = True
            isis2.advanced.lsp_lifetime = 1200
            isis2.advanced.lsp_mgroup_min_trans_interval = 5000
            isis2.advanced.lsp_refresh_rate = 900
            isis2.advanced.max_area_addresses = 3
            isis2.advanced.max_lsp_size = 1492
            isis2.advanced.psnp_interval = 2000
            isis2.advanced.enable_attached_bit = False
            int2 = isis2.interfaces.add(name="{1}isis2int{0}".format(dev+1, index2))
            int2.eth_name = e2.name
            int2.l2_settings.dead_interval = 30
            int2.l2_settings.hello_interval = 10
            int2.l2_settings.priority = 0
            int2.level_type = int2.LEVEL_1
            int2.metric = 10
            rr2 = isis2.v4_routes.add(name="{1}rr{0}".format(dev+1, index2))
            rr2.addresses.add(
                count=noofroutes, address=config_values["tx_rr_add1"][dev - 1], prefix=32
            )
            rr2.link_metric = 10
            rr2.origin_type = rr2.INTERNAL

    holder = 1
    for flowindex in range(noofflows):
        flow = config.flows.add(name=f"flow {flowindex + 1}")
        flow.tx_rx.device.tx_names = [tx_ip_list[flowindex]]
        flow.tx_rx.device.rx_names = [rx_ip_list[flowindex]]
        holder += 1
        if holder > noofdevices:
            holder = 1
        flow.size.fixed = size
        flow.duration.fixed_packets.packets = packets
        flow.metrics.enable = True

    l1.port_names = l1ports
    
    response = api.set_config(config)
    connect['set_response'] = response
    return connect


@pytest.fixture(scope='function')
def config_n_port_b2b_isis_bgp(connect):
    api = connect['api']
    noofports = connect['noofports']
    noofdevices=connect['noofdevices']
    noofflows=connect['noofflows']
    ports = connect['ports']
    packets = connect['packets']
    noofroutes=connect['noofroutes']
    size= connect['size']

    config = api.config()

    l1 = config.layer1.layer1()[0]
    l1.name = "l1"
    l1.speed = "speed_400_gbps"


    config_values = {}
    macs = get_macs("000000000011", 2 * noofdevices)
    config_values["tx_macs"], config_values["rx_macs"] = macs[::2], macs[1::2]
    config_values["vlan_ids"] = [str(i) for i in range(1, noofdevices + 1)]
    ip_adds = get_ip_addresses("10.10.2.1", 2 * noofdevices)
    config_values["tx_adds"], config_values["rx_adds"] = (
        ip_adds[::2],
        ip_adds[1::2],
    )
    if noofdevices > noofflows:
        setval = noofdevices
    else:
        setval = noofflows 
    config_values["tx_rr_add1"] = get_ip_addresses("200.1.0.0", setval)
    config_values["tx_rr_add2"] = get_ip_addresses("201.1.0.0", setval)
    next_hop_addr = get_ip_addresses("4.4.4.1", noofroutes)
    config_values["rx_rr_add1"] = get_ip_addresses("100.1.0.0", setval)
    config_values["rx_rr_add2"] = get_ip_addresses("101.1.0.0", setval)
    config_values["tx_adds"], config_values["rx_adds"] = (
        ip_adds[::2],
        ip_adds[1::2],
    )
    n = int(noofports/2)
    l1ports = []
    for iter in range(0,n):
        index1 = iter*2+1
        index2 = iter*2+2
        p1 = ports[index1]
        p2 = ports[index2]

        port1 = config.ports.add(name="port{0}".format(index1), location = p1)
        port2 = config.ports.add(name="port{0}".format(index2), location = p2)
        l1ports.append(port1.name)
        l1ports.append(port2.name)
        tx_ip_list = []
        rx_ip_list = []

        for dev in range(0, noofdevices):
            d1 = config.devices.device(name="{1}d{0}".format(dev+1,index1))[-1]
            e1 = d1.ethernets.ethernet(name="{1}eth{0}".format(dev+1,index1))[-1]
            e1.connection.port_name = port1.name
            e1.mac =  config_values["tx_macs"][dev - 1]
            e1.mtu = 1500
            ip1 = e1.ipv4_addresses.add()
            ip1.name = "{1}ip{0}".format(dev+1,index1)
            tx_ip_list.append(ip1.name)
            ip1.address = config_values["tx_adds"][dev - 1]
            ip1.gateway = config_values["rx_adds"][dev - 1]
            ip1.prefix = 24
            bgp1 = d1.bgp
            bgp1.router_id = config_values["tx_adds"][dev - 1]
            bgp1_int = bgp1.ipv4_interfaces.add()
            bgp1_int.ipv4_name = ip1.name
            peer1 = bgp1_int.peers.add()
            peer1.name = "{1}BGP Peer {0}".format(dev+1,index1)
            peer1.as_type = "ibgp"
            peer1.peer_address = config_values["rx_adds"][dev - 1]
            peer1.as_number = 65200
            isis1 = d1.isis
            isis1.name = "{1}ISIS{0}".format(dev+1, index1)
            isis1.system_id = "640000000001"
            isis1.basic.ipv4_te_router_id = config_values['tx_adds'][dev - 1]
            isis1.basic.hostname = "{1}ixia-c-port{0}".format(dev+1, index1)
            isis1.advanced.area_addresses = ["490001"]
            isis1.advanced.csnp_interval = 10000
            isis1.advanced.enable_hello_padding = True
            isis1.advanced.lsp_lifetime = 1200
            isis1.advanced.lsp_mgroup_min_trans_interval = 5000
            isis1.advanced.lsp_refresh_rate = 900
            isis1.advanced.max_area_addresses = 3
            isis1.advanced.max_lsp_size = 1492
            isis1.advanced.psnp_interval = 2000
            isis1.advanced.enable_attached_bit = False
            int1 = isis1.interfaces.add(name="{1}isis1int{0}".format(dev+1, index1))
            int1.eth_name = e1.name
            int1.l2_settings.dead_interval = 30
            int1.l2_settings.hello_interval = 10
            int1.l2_settings.priority = 0
            int1.level_type = int1.LEVEL_1
            int1.metric = 10
            rr1 = isis1.v4_routes.add(name="{1}rr{0}".format(dev+1, index1))
            rr1.addresses.add(
                count=noofroutes, address=config_values["rx_rr_add1"][dev - 1], prefix=32
            )
            rr1.link_metric = 10
            rr1.origin_type = rr1.INTERNAL


        for dev in range(0, noofdevices):
            d2 = config.devices.device(name="{1}d_{0}".format(dev+1,index2))[-1]
            e2 = d2.ethernets.ethernet(name="{1}eth_{0}".format(dev+1,index2))[-1]
            e2.connection.port_name = port2.name
            e2.mac =  config_values["rx_macs"][dev - 1]
            e2.mtu = 1500
            ip2 = e2.ipv4_addresses.add()
            ip2.name = "{1}ip_{0}".format(dev+1,index2)
            rx_ip_list.append(ip2.name)
            ip2.address = config_values["rx_adds"][dev - 1]
            ip2.gateway = config_values["tx_adds"][dev - 1]
            ip2.prefix = 24
            bgp2 = d2.bgp
            bgp2.router_id = config_values["rx_adds"][dev - 1]
            bgp2_int = bgp2.ipv4_interfaces.add()
            bgp2_int.ipv4_name = ip2.name
            peer2 = bgp2_int.peers.add()
            peer2.name = "{1}BGP Peer_ {0}".format(dev+1,index2)
            peer2.as_type = "ibgp"
            peer2.peer_address = config_values["tx_adds"][dev - 1]
            peer2.as_number = 65200
            isis2 = d2.isis
            isis2.name = "{1}ISIS{0}".format(dev+1, index2)
            isis2.system_id = "640000000001"
            isis2.basic.ipv4_te_router_id = config_values['tx_adds'][dev - 1]
            isis2.basic.hostname = "{1}ixia-c-port{0}".format(dev+1, index2)
            isis2.advanced.area_addresses = ["490001"]
            isis2.advanced.csnp_interval = 10000
            isis2.advanced.enable_hello_padding = True
            isis2.advanced.lsp_lifetime = 1200
            isis2.advanced.lsp_mgroup_min_trans_interval = 5000
            isis2.advanced.lsp_refresh_rate = 900
            isis2.advanced.max_area_addresses = 3
            isis2.advanced.max_lsp_size = 1492
            isis2.advanced.psnp_interval = 2000
            isis2.advanced.enable_attached_bit = False
            int2 = isis2.interfaces.add(name="{1}isis2int{0}".format(dev+1, index2))
            int2.eth_name = e2.name
            int2.l2_settings.dead_interval = 30
            int2.l2_settings.hello_interval = 10
            int2.l2_settings.priority = 0
            int2.level_type = int2.LEVEL_1
            int2.metric = 10
            rr2 = isis2.v4_routes.add(name="{1}rr{0}".format(dev+1, index2))
            rr2.addresses.add(
                count=noofroutes, address=config_values["tx_rr_add1"][dev - 1], prefix=32
            )
            rr2.link_metric = 10
            rr2.origin_type = rr2.INTERNAL
    holder = 1
    for flowindex in range(noofflows):
        flow = config.flows.add(name=f"flow {flowindex + 1}")
        flow.tx_rx.device.tx_names = [tx_ip_list[flowindex]]
        flow.tx_rx.device.rx_names = [rx_ip_list[flowindex]]
        holder += 1
        if holder > noofdevices:
            holder = 1
        flow.size.fixed = size
        flow.duration.fixed_packets.packets = packets
        flow.metrics.enable = True

    l1.port_names = l1ports
    
    response = api.set_config(config)
    connect['set_response'] = response
    return connect



        

