import pytest
from  utils.utils import *

def test_can_run_isis_bgp_sessions(config_n_port_b2b_isis_bgp):
    api = config_n_port_b2b_isis_bgp['api']
    num_of_devices = config_n_port_b2b_isis_bgp['noofdevices']
    packets = config_n_port_b2b_isis_bgp['packets']
    noofports = config_n_port_b2b_isis_bgp['noofports']
    timeout = config_n_port_b2b_isis_bgp['timeout']

    print("Starting protocols")
    protocol_state = api.protocol_state()
    protocol_state.state = "start"
    response = api.set_protocol_state(protocol_state)

    verifyISIS = verify(api, protocol="ISIS")
    verifyISIS.followSessionsOverTime(num_of_devices*noofports, timeout=timeout)
    verifyBGP = verify(api)
    verifyBGP.followSessionsOverTime(num_of_devices*noofports, timeout=timeout)
    print("Starting transmit on all flows ...")

    request = api.transmit_state()
    request.state = "start"
    response = api.set_transmit_state(request)
    res = verifyISIS.verifyTransmission(packets, timeout = timeout)
    assert res < 100

    print("Stopping transmit on all flows ...")

    request = api.transmit_state()
    request.state = "stop"
    response = api.set_transmit_state(request)