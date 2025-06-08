#!/usr/bin/env python3
# cython: language_level=3, always_allow_keywords=True
# vim:fileencoding=utf-8
# coding: utf-8
# -*- coding: utf-8 -*-

# dependences:
#   apt install python3-serial python3-nmea2 python3-jsonrpclib-pelix

import time
import sys
import os
import serial
import pynmea2
from jsonrpclib.jsonrpc import Server


def parse_nmea_data(port, baudrate, timeout=1):
    """
    Read and parse NMEA data from serial port

    Parameters:
        port (str): Serial device name, on Windows might be 'COM1', etc.
        baudrate (int): Baud rate
        timeout (int): Read timeout in seconds
    """
    try:
        # Open serial port with specified timeout
        ser = serial.Serial(port, baudrate, timeout=timeout)
        print(f"Successfully opened serial port: {port} with {timeout}s timeout")

        # Count consecutive timeouts
        timeout_count = 0
        max_timeouts = 5  # Maximum consecutive timeouts before action

        while True:
            try:
                # Read one line of data
                line = ser.readline().decode('ascii', errors='replace').strip()

                # Handle timeout (empty data)
                if not line:
                    timeout_count += 1
                    print(f"Timeout occurred ({timeout_count}/{max_timeouts})")

                    # Take action after multiple consecutive timeouts
                    if timeout_count >= max_timeouts:
                        print("Multiple consecutive timeouts. Check GPS connection.")
                        print("Resetting connection...")
                        ser.close()
                        time.sleep(1)
                        ser.open()
                        timeout_count = 0

                    continue

                # Reset timeout counter when data is received
                timeout_count = 0

                #print(f"Raw data: {line}")

                # Check if data is in NMEA format
                if line.startswith('$'):
                    try:
                        # Parse NMEA data
                        msg = pynmea2.parse(line)

                        # Print parsing results
                        #print(f"Message type: {msg.sentence_type}")

                        # Process different types of NMEA messages
                        if msg.sentence_type == 'GGA':  # GPS position data
                            print(f"Time: {msg.timestamp}")
                            print(f"Latitude: {msg.latitude} {msg.lat_dir}")
                            print(f"Longitude: {msg.longitude} {msg.lon_dir}")
                            print(f"Altitude: {msg.altitude} {msg.altitude_units}")
                            print(f"Number of satellites: {msg.num_sats}")
                            print(f"Position quality: {msg.gps_qual}")

                        elif msg.sentence_type == 'RMC':  # Recommended minimum positioning information
                            print(f"Time: {msg.timestamp}")
                            print(f"Date: {msg.datestamp}")
                            print(f"Latitude: {msg.latitude} {msg.lat_dir}")
                            print(f"Longitude: {msg.longitude} {msg.lon_dir}")
                            print(f"Speed (knots): {msg.spd_over_grnd}")
                            print(f"Course (degrees): {msg.true_course}")

                        elif msg.sentence_type == 'GSV':  # Visible satellite information
                            print(f"Total visible satellites: {msg.num_sv_in_view}")

                        # You can add processing for other NMEA message types as needed

                        print('-' * 50)
                    except pynmea2.ParseError as e:
                        print(f"Parsing error: {e}")

            except UnicodeDecodeError:
                print("Decoding error, skipping this line")

            except KeyboardInterrupt:
                print("Program interrupted by user")
                break

    except serial.SerialException as e:
        print(f"Failed to open serial port: {e}")

    finally:
        # Ensure the serial port is closed
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("Serial port closed")

td_hw_manager = Server(f'http://127.0.0.1:8800')

def start_gps():
    print(f'starting gps ...')
    results = td_hw_manager.rpc_ec800m_execute_command('AT+QGPS=1')
    if results['success'] == True or 'response' in results and results['response'][0] == '+CME ERROR: 504':
        print(f'starting gps(ec800m) success')
    else:
        print(f'starting gps(ec800m) fail: {results}')
        sys.exit(1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', type=str, default='/dev/ttyLP7', help = 'gps serial port name, default: %(default)s)')
    parser.add_argument('--baudrate', type=int, default=115200, help = 'gps serial port baudrate, default: %(default)s)')
    args = parser.parse_args()

    start_gps()
    parse_nmea_data(args.serial, args.baudrate)
