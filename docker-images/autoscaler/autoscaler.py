"""
This service will listen for incoming
computation times from the web app instances and
will calculate the average computation
time for the last 10 requests.

The autoscaler will then use this
average computation time to determine
whether to scale up or down.
"""

import json
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
    "monitoringIntervalSeconds": 5,  # How often to check the average computation time
}

client = docker.from_env()
app = Flask(__name__)
times = []
plots = {"times": [], "workloads": [], "replicas": []}
currTime = time.time()


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

        plots["times"].append([(time.time() - currTime), average])
        times.clear()
        time.sleep(CONFIG["monitoringIntervalSeconds"])


# real-time graph of response times
@app.route("/graph")
def graph():
    return Response(
        """
        <html>
        <head>
            <title>Response Times</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        </head>
        <body>
            <div id="graph"></div>
            <script>
                function updateGraph() {
                    fetch("/plots")
                        .then(response => response.json())
                        .then(plots => {
                            const {times} = plots;
                            Plotly.newPlot(graph, [{x: times.map(t => t[0]), y: times.map(t => t[1]), type: "line"}]);
                        });
                }

                setInterval(updateGraph, 1000);
            </script>
        </body>
        </html>
        """,
        mimetype="text/html",
    )


# plot the workload (requests per second) by seeing the amount of times in the last 15 seconds
@app.route("/workload")
def workload():
    return Response(
        """
        <html>
        <head>
            <title>Workload</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        </head>
        <body>
            <div id="graph"></div>
            <script>
                var times = [];
                var workload = [];
                var timeIndex = 0;
                var graph = document.getElementById("graph");
                var monitoringIntervalSeconds = """
        + CONFIG["monitoringIntervalSeconds"]
        + """;
                function updateGraph() {
                    fetch("/times")
                        .then(response => response.json())
                        .then(newTimes => {
                            if (newTimes.timeIndex > timeIndex) {
                                timeIndex = newTimes.timeIndex;
                                times = newTimes.times;
                                // calculate the workload
                                workload.concat(times.length / monitoringIntervalSeconds);
                            } else{
                                // if no new times, then the workload is 0
                                workload.concat(0);
                            }
                            Plotly.newPlot(graph, [{y: workload, type: "line"}]);
                        });
                }

                setInterval(updateGraph, 1000);
            </script>
        </body>
        </html>
        """,
        mimetype="text/html",
    )


@app.route("/plots")
def getTimes():
    return Response(
        json.dumps(plots),
        mimetype="application/json",
    )


if __name__ == "__main__":
    threading.Thread(target=monitor, args=(times,)).start()
    app.run(host="0.0.0.0", port=8001, debug=False)
