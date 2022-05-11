

from datetime import datetime, timedelta
import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import dash_daq as daq
import plotly
from dash.dependencies import Input, Output
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import time
import json
import os

###############################################################################

# set up initial dictionary to record sensor readings for line graphs
readings = [0, 0, 0, 0, 0, 0]
data_range = 100
start_time = datetime.now() - timedelta(seconds=data_range)
data = {
    'Time': [start_time + timedelta(seconds=x) for x in range(data_range)],
    'Temperature': [0 for x in range(data_range)],
    "Pressure": [0 for x in range(data_range)],
    "Humidity": [0 for x in range(data_range)],
    "Gas": [0 for x in range(data_range)],
    "Smoke": [0 for x in range(data_range)],
    "AirQ": [0 for x in range(data_range)]}


###############################################################################
# Custom MQTT message callback
def customCallback(client, userdata, message):
    global readings
    m = json.loads(message.payload.decode())
    readings = [m["readings"]]
    readings = readings[0]
    print(readings)
    return

###############################################################################
# set up MQTT connection to AWS
host = "a2z2lg09mryugj-ats.iot.us-east-1.amazonaws.com"
rootCAPath = "root-CA.crt"
certificatePath = "Sensor_2.cert.pem"
privateKeyPath = "Sensor_2.private.key"
clientId = "sdk-java"
topic = "sdk/test/Python"

# Port defaults
#port = 443
port = 8883

# Init AWSIoTMQTTClient
myAWSIoTMQTTClient = None
myAWSIoTMQTTClient = AWSIoTMQTTClient(clientId)
myAWSIoTMQTTClient.configureEndpoint(host, port)
myAWSIoTMQTTClient.configureCredentials(rootCAPath, privateKeyPath, certificatePath)

# AWSIoTMQTTClient connection configuration
myAWSIoTMQTTClient.configureAutoReconnectBackoffTime(1, 32, 20)
myAWSIoTMQTTClient.configureOfflinePublishQueueing(-1)
myAWSIoTMQTTClient.configureDrainingFrequency(2)
myAWSIoTMQTTClient.configureConnectDisconnectTimeout(10)
myAWSIoTMQTTClient.configureMQTTOperationTimeout(5)

# Connect and subscribe to AWS IoT
myAWSIoTMQTTClient.connect()
myAWSIoTMQTTClient.subscribe(topic, 1, customCallback)
time.sleep(2)

# Sibscribe to AWS topic
#loopCount = 0
#myAWSIoTMQTTClient.subscribe(topic, 1, customCallback)

###############################################################################
# set up dashboard
external_stylesheets = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]

#app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
#app.scripts.config.serve_locally = True
application = app.server

app.layout = html.Div([
        html.H1("Environment Dashboard"),
        html.H3("Sensor Readings"),

        #html.Div(id="live-update-text"),

        #html.H2("Gauges"),

        html.Div([
            daq.Gauge(
            id="my-gauge-1",
            size=250,
            scale={"start": 0, "interval": 5, "labelInterval": 1},
            color={"gradient":True,"ranges":{"blue":[0,15],"green":[15,22],"yellow":[22,28], "orange":[28,35],"red":[35,40]}},
            showCurrentValue=True,
            label="Temperature ('C)",
            units="Celsius",
            value=0,
            max=40,
            min=0,
        )],style={"display": "inline-block"}),

        html.Div([
            daq.Gauge(
            id="my-gauge-2",
            size=250,
            scale={"interval": 100, "labelInterval": 1},
            color={"gradient":True,"ranges":{"blue":[0,950],"green":[950,1020],"yellow":[1020,1100]}},
            showCurrentValue=True,
            label="Pressure (mb)",
            units="Millibars",
            value=0,
            max=1100,
            min=0,
        )],style={"display": "inline-block"}),

        html.Div([
            daq.Gauge(
            id="my-gauge-3",
            size=250,
            scale={"start": 0, "interval": 10, "labelInterval": 1},
            color={"gradient":True,"ranges":{"red":[0,10],"orange":[10,20],"yellow":[20,30],"green":[30,50],"blue":[50,100]}},
            showCurrentValue=True,
            label="Humidity (%)",
            units="%",
            value=0,
            max=100,
            min=0,
        )],style={"display": "inline-block"}),
        
        html.Div([
            daq.Gauge(
            id="my-gauge-4",
            size=250,
            scale={"start": 0, "interval": 10, "labelInterval": 1},
            color={"gradient":True,"ranges":{"red":[0,20],"orange":[20,30],"yellow":[30,40],"green":[40,100]}},
            showCurrentValue=True,
            label="Gas (k ohms)",
            units="k ohms",
            value=0,
            max=100,
            min=0,
        )],style={"display": "inline-block"}),
        
        html.Div([
            daq.Gauge(
            id="my-gauge-5",
            size=250,
            scale={"start": 0, "interval": 10, "labelInterval": 1},
            color={"gradient":True,"ranges":{"red":[0,50],"orange":[50,70],"yellow":[70,85],"green":[85,100]}},
            showCurrentValue=True,
            label="Air Quality %",
            units="Quality",
            value=0,
            max=100,
            min=0,
        )],style={"display": "inline-block"}),

        #html.H3("Graphs"),

        dcc.Graph(id="live-update-graph"),

        dcc.Interval(
            id="interval-component",
            interval=1*2000, # in milliseconds
            n_intervals=0
        )
    ])

###############################################################################
# dash callbacks and functions for each of the gauges, charts and information

@app.callback(Output('my-gauge-1', 'value'), Input('interval-component', 'n_intervals'))
def temperature_gauge(value):
    # return temperature reading from AWS MQTT Subscription
    value = readings[0]
    return value

@app.callback(Output('my-gauge-2', 'value'), Input('interval-component', 'n_intervals'))
def pressure_gauge(value):
    # return pressure reading from AWS MQTT Subscription
    value = readings[1]
    return value

@app.callback(Output('my-gauge-3', 'value'), Input('interval-component', 'n_intervals'))
def humidity_gauge(value):
    # return humidity reading from AWS MQTT Subscription
    value = readings[2]
    return value

@app.callback(Output('my-gauge-4', 'value'), Input('interval-component', 'n_intervals'))
def gas_gauge(value):
    # return gas reading from AWS MQTT Subscription
    value = readings[3]/1000
    return value

@app.callback(Output('my-gauge-5', 'value'), Input('interval-component', 'n_intervals'))
def air_quality(value):
    # return air quality reading from AWS MQTT Subscription
    value = readings[4]
    return value

###############################################################################
# callbacks and functions for creating the graphs
@app.callback(Output('live-update-graph', 'figure'),
              Input('interval-component', 'n_intervals'))
def temperature_graph(n):
    # temperature graph over time
    global data, temp
    time = datetime.now()
    temp = int(readings[0])
    humi = int(readings[2])
    gas = int(readings[3]/1000)
    airq = int(readings[4])
    data["Time"].append(time)
    data["Temperature"].append(temp)
    data["Humidity"].append(humi)
    data["Gas"].append(gas)
    data["AirQ"].append(airq)

    if len(data["Time"]) > data_range:
        data["Time"].pop(0)
        data["Temperature"].pop(0)
        data["Humidity"].pop(0)
        data["Gas"].pop(0)
        data['AirQ'].pop(0)
    fig = plotly.tools.make_subplots(rows=1, cols=4, vertical_spacing=0.2, shared_yaxes=True,
                                     subplot_titles=("Temp {}'c".format(temp), "AirQ {}%".format(airq),
                                     "Humidity {}%".format(humi), "Gas {} k ohms".format(gas)))
    fig['layout']['legend'] = {'x': 0, 'y': 1, 'xanchor': 'left'}
    fig['layout']['width'] = 1600
    fig['layout']['height'] = 400
    fig["layout"]["template"] = "plotly_dark"
    fig.update_layout(yaxis_range=[0,100])
    
    fig.append_trace({
        'x': data['Time'],
        'y': data['Temperature'],
        'name': 'T',
        'mode': 'lines',
        'type': 'scatter'
    }, 1, 1)
    
    fig.append_trace({
        'x': data['Time'],
        'y': data['AirQ'],
        'name': 'AQ',
        'mode': 'lines',
        'type': 'scatter'
    }, 1, 2)

    fig.update_layout(yaxis_range=[0,100])
    fig.append_trace({
        'x': data['Time'],
        'y': data['Humidity'],
        'name': 'Hu',
        'mode': 'lines',
        'type': 'scatter'
    }, 1, 3)

    fig.append_trace({
        'x': data['Time'],
        'y': data['Gas'],
        'name': 'Gs',
        'mode': 'lines',
        'type': 'scatter'
    }, 1, 4)

    return fig


if __name__ == '__main__':
    application.run(debug=True, port=8080)
