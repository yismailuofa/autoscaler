"""
This service will listen for incoming
computation times from the web app instances and
will calculate the average computation
time for the last 10 requests.

The autoscaler will then use this
average computation time to determine
whether to scale up or down.
"""

from flask import Flask, Response
from collections import deque

CONFIG = {
    "maxInstances": 5, # Maximum number of instances to scale up to
    "minInstances": 1, # Minimum number of instances to scale down to
    "scaleUpThresholdSeconds": 0.8, # Scale up if the average computation time is greater than this
    "scaleDownThresholdSeconds": 0.5, # Scale down if the average computation time is less than this
    "scaleUpRatio": 2, # Scale up by this ratio
    "monitoringIntervalSeconds": 10 # How often to check the average computation time
}

app = Flask(__name__)
averageTimes = deque([])

@app.route('/time', methods=['POST'])
def updateTimes():
    # TODO maybe sliding window?

    return Response(status=200) 

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001, debug=True)