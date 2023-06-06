import pytest
from  utils.utils import *

def test_can_run_isis_sessions(config_n_port_b2b_isis):
    api = config_n_port_b2b_isis['api']
    num_of_devices = config_n_port_b2b_isis['noofdevices']
    packets = config_n_port_b2b_isis['packets']
    noofports = config_n_port_b2b_isis['noofports']
    timeout = config_n_port_b2b_isis['timeout']

    print("Starting protocols")
    protocol_state = api.protocol_state()
    protocol_state.state = "start"
    response = api.set_protocol_state(protocol_state)

    verify1 = verify(api, protocol="ISIS")
    verify1.followSessionsOverTime(num_of_devices*noofports, timeout=timeout)
    print("Starting transmit on all flows ...")

    request = api.transmit_state()
    request.state = "start"
    response = api.set_transmit_state(request)
    res = verify1.verifyTransmission(packets, timeout = timeout)
    assert res < 100

    print("Stopping transmit on all flows ...")

    request = api.transmit_state()
    request.state = "stop"
    response = api.set_transmit_state(request)