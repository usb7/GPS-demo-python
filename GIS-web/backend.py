#!/usr/bin/env python3
# cython: language_level=3, always_allow_keywords=True
# vim:fileencoding=utf-8
# coding: utf-8
# -*- coding: utf-8 -*-

# dependences:
#   apt install python3-flask-cors python3-serial python3-nmea2 python3-jsonrpclib-pelix

from collections import deque

import serial
import pynmea2
import time
import json
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import threading
from jsonrpclib.jsonrpc import Server

app = Flask(__name__, static_folder='static')
CORS(app)

# store newest GPS data
gps_data = {
    "latitude": 0,
    "longitude": 0,
    "timestamp": "",
    "speed": 0,
    "altitude": 0,
    "satellites": 0,
    "status": "not connected"
}

queue_num_sv_in_view = deque(maxlen=6)

def read_gps(serial_port, baudrate):
    global gps_data

    while True:
        try:
            # 尝试打开串口
            with serial.Serial(serial_port, baudrate, timeout=1) as ser:
                gps_data["status"] = "connected"
                print("GPS device is connected")

                while True:
                    try:
                        # read one line
                        line = ser.readline().decode('ascii', errors='replace').strip()

                        if line.startswith('$'):
                            # Parse NMEA data
                            msg = pynmea2.parse(line)

                            # Print parsing results
                            #print(f"Message type: {msg.sentence_type}")

                            # Process different types of NMEA messages
                            if msg.sentence_type == 'GGA':  # GPS position data
                                # print(f"Time: {msg.timestamp}")
                                # print(f"Latitude: {msg.latitude} {msg.lat_dir}")
                                # print(f"Longitude: {msg.longitude} {msg.lon_dir}")
                                # print(f"Altitude: {msg.altitude} {msg.altitude_units}")
                                # print(f"Number of satellites: {msg.num_sats}")
                                # print(f"Position quality: {msg.gps_qual}")
                                gps_data["latitude"] = msg.latitude
                                gps_data["longitude"] = msg.longitude
                                gps_data["altitude"] = msg.altitude

                            elif msg.sentence_type == 'RMC':  # Recommended minimum positioning information
                                # print(f"Time: {msg.timestamp}")
                                # print(f"Date: {msg.datestamp}")
                                # print(f"Latitude: {msg.latitude} {msg.lat_dir}")
                                # print(f"Longitude: {msg.longitude} {msg.lon_dir}")
                                # print(f"Speed (knots): {msg.spd_over_grnd}")
                                # print(f"Course (degrees): {msg.true_course}")
                                gps_data["timestamp"] = f"{msg.datetime.strftime('%Y-%m-%d %H:%M:%S')}"
                                gps_data["latitude"] = msg.latitude
                                gps_data["longitude"] = msg.longitude
                                gps_data["speed"] = msg.spd_over_grnd * 1.852 if msg.spd_over_grnd else 0  # 转换为km/h

                            elif msg.sentence_type == 'GSV':  # Visible satellite information
                                # print(f"Total visible satellites: {msg.num_sv_in_view}")
                                queue_num_sv_in_view.append(msg.num_sv_in_view)
                                gps_data["satellites"] = max(queue_num_sv_in_view)

                            # You can add processing for other NMEA message types as needed

                            # print('-' * 50)
                    except Exception as e:
                        print(f"parse error: {e}")
                        continue

        except serial.SerialException as e:
            print(f"can't connect gps: {e}")
            gps_data["status"] = "fail connect"
            time.sleep(5)

        except Exception as e:
            print(f"exception: {e}")
            gps_data["status"] = "exception"
            time.sleep(5)

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/gps')
def get_gps():
    return jsonify(gps_data)

td_hw_manager = Server(f'http://127.0.0.1:8800')

def start_gps():
    print(f'starting gps ...')
    results = td_hw_manager.rpc_ec800m_execute_command('AT+QGPS=1')
    if results['success'] == True or 'response' in results and results['response'][0] == '+CME ERROR: 504':
        print(f'starting gps(ec800m) success')
    else:
        print(f'starting gps(ec800m) fail: {results}')
        sys.exit(1)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', nargs = 1, type=str, default='/dev/ttyLP7', help = 'gps serial port name, default: %(default)s)')
    parser.add_argument('--baudrate', nargs = 1, type=int, default=115200, help = 'gps serial port baudrate, default: %(default)s)')
    args = parser.parse_args()

    start_gps()

    gps_thread = threading.Thread(target=read_gps, daemon=True, kwargs={"serial_port": args.serial, "baudrate": args.baudrate})
    gps_thread.start()

    app.run(host='0.0.0.0', port=8801, debug=True, use_reloader=False)