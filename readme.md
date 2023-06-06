you can use fllowng command to run tests.
pytest tests/protocols/test_isis_bgp.py --controller obox0.lbj.is.keysight.com:40051 --noofdevices 10 --noofports 4 --noofflows 4 --noofpkts 1000 --framesize 128 --sessiontimeout 120

controller : default is given as localhost:40051
noofdevices : the number of devices to be configured per port
noofports : noofports to be used. since we are using b2b we need pairs. hence as of we can go up to 16 ports. The ports will be implicitly read from the binding file that has been created and copied in the test directory using olab(http://gitlab-proxy.do.nas.is.keysight.com/p4isg/orbit/orbit-lab-op.git). this needs to be updated as per the latest binding with uhd.
noofflows : number of flows per pair of ports.
noofpkts : number of pkts per flow
framesize
sessiontimeout: this will watch the session for the mentioned timeout and then check if all are up and doing well.