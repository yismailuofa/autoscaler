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
from flask import Flask, Response, request
from collections import deque
import docker

CONFIG = {
    "maxInstances": 5, # Maximum number of instances to scale up to
    "minInstances": 1, # Minimum number of instances to scale down to
    "scaleUpThresholdSeconds": 0.8, # Scale up if the average computation time is greater than this
    "scaleDownThresholdSeconds": 0.5, # Scale down if the average computation time is less than this
    "scaleUpRatio": 2, # Scale up by this ratio
    "monitoringIntervalSeconds": 10 # How often to check the average computation time
}

client = docker.from_env()

app = Flask(__name__)
# keep a sliding window of the last 100 computation times
averageTimes = deque(100*[0], maxlen=100)

@app.route('/time', methods=['POST'])
def updateTimes():
    # TODO maybe sliding window?
    averageTimes.append(float(request.data))
    return Response(status=200) 

# in a separate thread, monitor the average computation time
# and scale up or down accordingly
def monitor():
    while True:
        # get the average computation time
        averageTimesList = list(averageTimes)
        average = sum(averageTimesList) / len(averageTimesList)
        service = client.services.get('my_service')
        # Check the current scale
        current_scale = service.attrs['Spec']['Mode']['Replicated']['Replicas']

        # Scale the service
        service.scale(new_scale)
        print(f"Average Times: {average}")
        # scale up or down
        if average > CONFIG["scaleUpThresholdSeconds"]:
            # Calculate the new scale
            new_scale = int(current_scale * CONFIG["scaleUpRatio"])
            # scale up
            service.scale(min(new_scale, CONFIG["maxInstances"]))
        elif average < CONFIG["scaleDownThresholdSeconds"]:
            # scale down
            # Calculate the new scale
            new_scale = int(current_scale // CONFIG["scaleUpRatio"])
            # scale up
            service.scale(max(new_scale, CONFIG["minInstances"]))
        else:
            # do nothing
            pass
        # sleep for the monitoring interval
        time.sleep(CONFIG["monitoringIntervalSeconds"])

if __name__ == "__main__":
    # spawn a thread to monitor the average computation time and scale up or down accordingly
    threading.Thread(target=monitor).start()
    app.run(host="0.0.0.0", port=8001, debug=True)