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

        newTime = time.time() - currTime
        plots["times"].append([newTime, average])
        plots["workloads"].append(
            [newTime, len(times) / CONFIG["monitoringIntervalSeconds"]]
        )
        plots["replicas"].append([newTime, newScale])

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
            <div id="times-graph"></div>
            <div id="workload-graph"></div>
            <div id="replicas-graph"></div>
            <script>
                function updateGraph() {
                    fetch("/plots")
                        .then(response => response.json())
                        .then(plots => {
                            const {times, workloads, replicas} = plots;

                            const timesLayout = {
                                title: "Response Times",
                                xaxis: {title: "Seconds since server start"}
                                yaxis: {title: "Response Time (s)"},

                            };
                            const workloadLayout = {
                                title: "Workload",
                                xaxis: {title: "Seconds since server start"}
                                yaxis: {title: "Workload (req/s)"},
                            };

                            const replicasLayout = {
                                title: "Web-app Replicas",
                                xaxis: {title: "Seconds since server start"}
                                yaxis: {title: "Replicas"},
                            };

                            Plotly.react("times-graph", [{x: times.map(t => t[0]), y: times.map(t => t[1]), type: "line"}], timesLayout);
                            Plotly.react("workload-graph", [{x: workloads.map(t => t[0]), y: workloads.map(t => t[1]), type: "line"}], workloadLayout);
                            Plotly.react("replicas-graph", [{x: replicas.map(t => t[0]), y: replicas.map(t => t[1]), type: "line"}], replicasLayout);   
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
