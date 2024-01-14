"""
This service will listen for incoming
computation times from the web app instances and
will calculate the average computation
time for the last 10 requests.

The autoscaler will then use this
average computation time to determine
whether to scale up or down.
"""

import threading
import time
import docker
from flask import Flask, Response, request

CONFIG = {
    "maxInstances": 5,  # Maximum number of instances to scale up to
    "minInstances": 1,  # Minimum number of instances to scale down to
    "scaleUpThresholdSeconds": 4.0,  # Scale up if the average computation time is greater than this
    "scaleDownThresholdSeconds": 2.5,  # Scale down if the average computation time is less than this
    "scaleAmount": 1,  # How much to scale up or down by
    "monitoringIntervalSeconds": 15,  # How often to check the average computation time
}

client = docker.from_env()
app = Flask(__name__)
times = []


@app.route("/time", methods=["POST"])
def updateTimes():
    times.append(float(request.data))

    return Response(status=200)


def monitor(times):
    while True:
        average = sum(times) / max(len(times), 1)
        print("Average time: {}".format(average))
        service = [s for s in client.services.list() if "web" in s.name][0]
        newScale = currScale = service.attrs["Spec"]["Mode"]["Replicated"]["Replicas"]

        if average > CONFIG["scaleUpThresholdSeconds"]:
            newScale = min(
                int(currScale + CONFIG["scaleAmount"]), CONFIG["maxInstances"]
            )
        elif average < CONFIG["scaleDownThresholdSeconds"]:
            newScale = max(
                int(currScale - CONFIG["scaleAmount"]), CONFIG["minInstances"]
            )

        if newScale != currScale:
            print(f"Scaling from {currScale} to {newScale}")
            service.scale(newScale)

        times.clear()
        time.sleep(CONFIG["monitoringIntervalSeconds"])


if __name__ == "__main__":
    threading.Thread(target=monitor, args=(times,)).start()
    app.run(host="0.0.0.0", port=8001, debug=False)
