from flask import Flask, render_template, request
import requests
import json
from datetime import datetime
import csv
from activate import process_activation

app = Flask(__name__)
global_token = ""


@app.route('/activate', methods=['GET', 'POST'])
def activate_app():
    global global_token
    api_token = ""
    if request.method == 'POST':
        token = request.form['token']
        print(token)
        if len(token) > 17:
            api_token = process_activation(token)
            global_token = api_token
        else:
            api_token = "Invalid"

    return render_template('activate.html', api_token=api_token)


def timestamp_to_date(timestamp):
    try:
        date = datetime.fromtimestamp(timestamp / 1000)
    except OSError:
        date = "No Date"
    return str(date)


def validate_token(check_token):
    return True


@app.route('/', methods=['GET', 'POST'])
def get_ble_telemetry_data():
    global global_token
    token = ""
    ble_mac_list = []
    ble_mac_names = {}
    ble_tags = {}
    ble_count = 0
    tag_updates = []
    start_time = datetime.now()
    process_time_secs = 0.0
    max_wait_secs = 10
    ble_mac_str = ""
    if global_token == "" and request.method == 'GET':
        return render_template('activate.html', api_token="")
    elif global_token == "" and request.method == 'POST':
        token = request.form['token']
        print(token)
        if len(token) > 17:
            api_token = process_activation(token)
            if api_token is None:
                return render_template('activate.html', api_token="")
            else:
                global_token = api_token
                return render_template('index.html', ble_tags={}, time_taken=0.0, api_token=global_token,
                                       ble_mac_str="", ble_mac_names={})
    else:
        if request.method == 'POST':
            token = request.form.get('api_token')
            ble_mac_str = request.form.get('ble_mac')
            if len(ble_mac_str) > 17:
                lines = ble_mac_str.splitlines()
                reader = csv.reader(lines, delimiter=',')
                next(reader, None)  # skip the headers
                for row in reader:
                    ble_mac_list.append(row[0])
                    ble_mac_names[row[0]] = row[5]
            headers = {'X-API-Key': global_token}
            # Connect to API
            stream_api = requests.get('https://partners.dnaspaces.io/api/partners/v1/firehose/events',
                                      stream=True, headers=headers)
            if stream_api.status_code == 200:
                # Read in an update from Firehose API
                for line in stream_api.iter_lines():
                    data = json.loads(line)
                    # Only process IOT events
                    if data['eventType'] == "IOT_TELEMETRY":
                        ble_count = ble_count + 1
                        device_id = data['iotTelemetry']['deviceInfo']['deviceMacAddress']
                        # Only grab details for tags we are interested in
                        if device_id in ble_mac_list and 'iBeacon' not in data['iotTelemetry']:
                            print(data)
                            if device_id not in ble_tags:
                                ble_tags[device_id] = {}
                            ble_tags[device_id]['x'] = data['iotTelemetry']['detectedPosition']['xPos']
                            ble_tags[device_id]['y'] = data['iotTelemetry']['detectedPosition']['yPos']
                            ble_tags[device_id]['floor'] = data['iotTelemetry']['location']['name']
                            # Some tags only provide extra telemetry data so we need to check
                            if 'temperature' in data['iotTelemetry']:
                                ble_tags[device_id]['temperature'] = \
                                    round(data['iotTelemetry']['temperature']['temperatureInCelsius'], 1)
                            if 'battery' in data['iotTelemetry']:
                                ble_tags[device_id]['battery'] = data['iotTelemetry']['battery']['value']
                            if 'accelerometer' in data['iotTelemetry']:
                                ble_tags[device_id]['accelerometer'] = \
                                    timestamp_to_date(data['iotTelemetry']['accelerometer']['lastMovementTimestamp'])
                            if 'pirTrigger' in data['iotTelemetry']:
                                pir_trigger = timestamp_to_date(data['iotTelemetry']['pirTrigger']['timestamp'])
                                if 'pirTrigger' in ble_tags[device_id].keys():
                                    if ble_tags[device_id]['pirTrigger'] < pir_trigger:
                                        print("NEW PIR date to", pir_trigger)
                                        ble_tags[device_id]['pirTrigger'] = pir_trigger
                                else:
                                    ble_tags[device_id]['pirTrigger'] = pir_trigger
                                    record_timestamp = timestamp_to_date(data['recordTimestamp'])
                                    print("First PIR update", record_timestamp, device_id,
                                          ble_tags[device_id]['pirTrigger'])
                            if 'deviceRtcTime' in data['iotTelemetry']:
                                ble_tags[device_id]['clock'] = timestamp_to_date(data['iotTelemetry']['deviceRtcTime'])
                            if device_id not in tag_updates:
                                tag_updates.append(device_id)
                        # Only grab 10 IOT updates
                        process_time_secs = round((datetime.now() - start_time).total_seconds(), 1)
                        if len(tag_updates) >= len(ble_mac_list) or process_time_secs > max_wait_secs:
                            print('Complete. Time taken', process_time_secs)
                            break
        return render_template('index.html', ble_tags=ble_tags, time_taken=process_time_secs, api_token=global_token,
                               ble_mac_str=ble_mac_str, ble_mac_names=ble_mac_names)


if __name__ == '__main__':
    app.run()
