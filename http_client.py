"""
HTTP client simulator. It simulate a number of concurrent users and calculate the response time for each request.
"""

import numpy as np
import requests
import time
import threading
import sys

if len(sys.argv) < 4:
    print('To few arguments; you need to specify 3 arguments.')
    print('Default values will be used for server_ip, no of users and think time.\n')
    swarm_master_ip = '10.2.9.108'  # ip address of the Swarm master node
    no_users = 1  # number of concurrent users sending request to the server
    think_time = 1  # the user think time (seconds) in between consequent requests
else:
    print('Default values have be overwritten.')
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
    # sleep for a time that grows and shrinks in a bell curve

    # Parameters
    a = 0.1  # Adjust this to change the steepness of the curve
    b = 0
    c = 1    # This is the maximum sleep time at the peak of the curve
    n = 10   # Range from -n to n

    while True:
        for x in np.linspace(-n, n, 2*n+1):
            sleep_time = -(a*x**2 + b*x + c)  # Inverted parabola
            sleep_time = max(sleep_time, 0)   # Ensure non-negative sleep time
            
            t0 = time.time()
            requests.get('http://' + swarm_master_ip + ':8000/')
            t1 = time.time()
            time.sleep(sleep_time)
            print("Response Time for " + user + " = " + str(t1 - t0))


if __name__ == "__main__":
    threads = []
    for i in range(no_users):
        threads.append(MyThread("User", i))

    for i in range(no_users):
        threads[i].start()

    for i in range(no_users):
        threads[i].join()
