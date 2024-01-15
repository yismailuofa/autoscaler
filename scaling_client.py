"""
HTTP client simulator. It simulate a number of concurrent users and calculate the response time for each request.
"""

import requests
import time
import threading
import sys
from requests.adapters import HTTPAdapter, Retry

if len(sys.argv) < 4:
    print("To few arguments; you need to specify 3 arguments.")
    print("Default values will be used for server_ip, no of users and think time.\n")
    swarm_master_ip = "10.2.9.108"  # ip address of the Swarm master node
    no_users = 1  # number of concurrent users sending request to the server
    think_time = 1  # the user think time (seconds) in between consequent requests
else:
    print("Default values have be overwritten.")
    swarm_master_ip = sys.argv[1]
    no_users = int(sys.argv[2])
    think_time = float(sys.argv[3])


class MyThread(threading.Thread):
    def __init__(self, name, counter):
        threading.Thread.__init__(self)
        self.threadID = counter
        self.name = name
        self.counter = counter

    def run(self):
        print("Starting " + self.name + str(self.counter))
        workload(self.name + str(self.counter))


def workload(user):
    t0 = time.time()
    sendRequest()
    t1 = time.time()
    time.sleep(think_time)
    print("Response Time for " + user + " = " + str(t1 - t0))


def sendRequest():
    with requests.Session() as s:
        s.mount("http://", HTTPAdapter(max_retries=Retry(total=5, backoff_factor=1)))
        s.get("http://" + swarm_master_ip + ":8000/")


if __name__ == "__main__":
    requestsPerSec = [*range(1, no_users + 1), *range(no_users - 1, 0, -1)]
    requestDuration = 60  # seconds
    totalDuration = len(requestsPerSec) * requestDuration

    start = time.time()

    while time.time() - start < totalDuration:
        req = requestsPerSec[int((time.time() - start) // requestDuration)]

        threads = []
        for i in range(req):
            threads.append(MyThread("User", i))

        for i in range(req):
            threads[i].start()

        for i in range(req):
            threads[i].join()
