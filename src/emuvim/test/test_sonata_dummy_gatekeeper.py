import time
import requests
import os
from emuvim.test.base import SimpleTestTopology
from emuvim.api.sonata import SonataDummyGatekeeperEndpoint



class testSonataDummyGatekeeper(SimpleTestTopology):

    def testAPI(self):
        # create network
        self.createNet(nswitches=0, ndatacenter=2, nhosts=2, ndockers=0)
        # setup links
        self.net.addLink(self.dc[0], self.h[0])
        self.net.addLink(self.dc[0], self.dc[1])
        self.net.addLink(self.h[1], self.dc[1])
        # connect dummy GK to data centers
        sdkg1 = SonataDummyGatekeeperEndpoint("0.0.0.0", 5000)
        sdkg1.connectDatacenter(self.dc[0])
        sdkg1.connectDatacenter(self.dc[1])
        # run the dummy gatekeeper (in another thread, don't block)
        sdkg1.start()
        # start Mininet network
        self.startNet()
        time.sleep(1)

        # download example from GitHub
        print "downloading latest son-demo.son from GitHub"
        download = requests.get("https://github.com/sonata-nfv/son-schema/blob/master/package-descriptor/examples/sonata-demo.son?raw=true")
        with open("son-demo.son", 'wb') as f:
            f.write(download.content)

        print "starting tests"
        # board package
        files = {"file": open("son-demo.son", "rb")}
        r = requests.post("http://127.0.0.1:5000/api/packages", files=files)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json().get("service_uuid") is not None)
        os.remove("son-demo.son")

        # instantiate service
        service_uuid = r.json().get("service_uuid")
        r2 = requests.post("http://127.0.0.1:5000/api/instantiations", json={"service_uuid": service_uuid})
        self.assertEqual(r2.status_code, 200)

        # give the emulator some time to instantiate everything
        time.sleep(2)

        # check get request APIs
        r3 = requests.get("http://127.0.0.1:5000/api/packages")
        self.assertEqual(len(r3.json().get("service_uuid_list")), 1)
        r4 = requests.get("http://127.0.0.1:5000/api/instantiations")
        self.assertEqual(len(r4.json().get("service_instance_list")), 1)

        # check number of running nodes
        self.assertTrue(len(self.getDockernetContainers()) == 3)
        self.assertTrue(len(self.net.hosts) == 5)
        self.assertTrue(len(self.net.switches) == 2)
        # check compute list result
        self.assertTrue(len(self.dc[0].listCompute()) == 3)
        # check connectivity by using ping
        for vnf in self.dc[0].listCompute():
            self.assertTrue(self.net.ping([self.h[0], vnf]) <= 0.0)
        # stop Mininet network
        self.stopNet()


