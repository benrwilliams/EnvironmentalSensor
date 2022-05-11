#!/usr/bin/env python
"""
Home Environment Sensor program
by Ben Williams 2022

Revision history
Version Date       Notes
======================================================================
v0.2    20/03/2022 Updated to include AWS IOT MQTT publishing code
        09/04/2022 updated to use 2nd LED display (now 4 characters)

"""

# =====================================================================
# import libraries for controlling breakout boards
from ltp305 import LTP305                   # lcd display library
from max30105 import MAX30105, HeartRate    # particle & heart rate sensor library
from trackball import TrackBall             # trackball library
import bme680                               # environment sensor library
# import libraries for interfacing with AWS via MQTT Link
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

# import supporting libraries
import json
from time import sleep
from datetime import datetime
import os
import sys
# change directory to location of certificates and keys for AWS IOT
os.chdir("/home/pi/Sensor2")

# =====================================================================
# set up AWS MQTT client
host = "a2z2lg09mryugj-ats.iot.us-east-1.amazonaws.com"
rootCAPath = "root-CA.crt"
certificatePath = "Sensor_2.cert.pem"
privateKeyPath = "Sensor_2.private.key"
clientId = "basicPubSub"
topic = "sdk/test/Python"

# flag used to determine whether to broadcast via MQTT to AWS IOT or not
MQTT_broadcast = True                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             

# Port defaults
port = 443
port = 8883

# Init AWSIoTMQTTClient
if MQTT_broadcast == True:
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


# =====================================================================
# set up the breakout boards attached to the Raspberry Pi
# initialise the lcd display
display = LTP305(address=97)
display.clear()
display.show()

# initialise trackball and set up colours for led light
trackball = TrackBall(interrupt_pin=4)
trackball.set_rgbw(0, 0, 0, 0)
trackball_colours = [[0, 0, 0],         # off
                    [255, 0, 0],        # red
                    [0, 255, 0],        # green
                    [0, 0, 255],        # blue
                    [255, 150, 255]]    # purple

# initialise particle detection sensor (heart rate sensor)
max30105 = MAX30105()
max30105.setup(leds_enable=3)
max30105.set_led_pulse_amplitude(1, 0.0)
max30105.set_led_pulse_amplitude(2, 0.0)
max30105.set_led_pulse_amplitude(3, 12.5)
max30105.set_slot_mode(1, 'red')
max30105.set_slot_mode(2, 'ir')
max30105.set_slot_mode(3, 'green')
max30105.set_slot_mode(4, 'off')

hr = HeartRate(max30105)

# initialise bme688 environment sensor
try:
    sensor = bme680.BME680(bme680.I2C_ADDR_PRIMARY)
except:
    sensor = bme680.BME680(bme680.I2C_ADDR_SECONDARY)
    
sensor.set_humidity_oversample(bme680.OS_2X)
sensor.set_pressure_oversample(bme680.OS_4X)
sensor.set_temperature_oversample(bme680.OS_8X)
sensor.set_filter(bme680.FILTER_SIZE_3)
sensor.set_gas_status(bme680.ENABLE_GAS_MEAS)                          
sensor.set_gas_heater_temperature(320)
sensor.set_gas_heater_duration(150)
sensor.select_gas_heater_profile(0)

# text to show on the led matrix display
display_names = ["TIME", "TEMP", "PRES", "HUMI", "GAS ", "SMOK", "AirQ"]

# lower / upper limits for warnings (light trackball led RED)
# values set for testing purposes only
warnings = [[5, 25],          # temp
            [980, 1300],      # pressure
            [30, 50],         # humidity
            [30000, 1000000],  # gas resistance
            [80, 100],       # smoke
            [50, 10000]]        # air quality

# =====================================================================
#### Trackball functions #####################
def read_trackball():
    """
    read trackball sensor data
    return "np" if not pressed
    return "sp" if short press
    return "lp" if long press
    nb - currently only the button status is being read
    """
    tb_read = trackball.read()
    button = tb_read[4]
    state = tb_read[5]
    if button > 0 and state == True:
        sleep(0.5)
        state = trackball.read()[5]
        if state == False:
            # short press
            return "sp"
        else:
            # long press
            return "lp"
    # no press
    return "np"

def light_trackball(colour):
    # illuminate trackball with a set colour, by name of colour
    r, g, b = trackball_colours[colour]
    trackball.set_rgbw(r, g, b, 0)
    return

# =====================================================================
### LCD Display functions ####################

def draw_lcd(string, decimal=0):
    """
    displays string across the 2 led matrix displays
    """
    if len(string) > 4:
        return
    # left-most display
    display = LTP305(address=99)
    display.clear()
    display.set_character(0, string[0])
    display.set_character(5, string[1])
    display.show()
    
    # right-most display
    display = LTP305(address=97)
    display.clear()
    display.set_character(0, string[2])
    display.set_character(5, string[3])
    display.set_decimal(left=decimal)
    display.show()
    return

def bright_lcd(level):
    if level == True:
        display = LTP305(address=99)
        display.set_brightness(1, True)
        display = LTP305(address=97)
        display.set_brightness(1, True)
    else:
        display = LTP305(address=99)
        display.set_brightness(0.25, True)
        display = LTP305(address=97)
        display.set_brightness(0.25, True)
    return

# =====================================================================
### Read Environment Sensor functions ########

# max30105 air particle (and heart rate) sensor
def read_max30105():
    samples = max30105.get_samples()
    reading = 0
    temp = 0
    if samples is not None:
        r = samples[2] & 0xff
        reading = hr.low_pass_fir(r)
        sleep(0.05)
        temp = max30105.get_temperature()
    return [reading, temp]    

# bme680 4-in-1 environmental sensor
def read_environment():
    if sensor.get_sensor_data():
        raw_temp = sensor.data.temperature
        raw_humi = sensor.data.humidity
        # limit humidity to max readining of '99.9%'
        raw_humi = min(raw_humi, 99.9)
        raw_pres = sensor.data.pressure
        if sensor.data.heat_stable:
            raw_gas = int(sensor.data.gas_resistance)
        else:
            raw_gas = 0
        return [raw_temp, raw_pres, raw_humi, raw_gas]
    return [0, 0, 0, 0]

def format_readings(sensor_readings):
    # format readings to 4 character strings including unit/measure
    raw_temp, raw_pres, raw_humi, raw_gas, airq, raw_smoke = sensor_readings
    temp = str(round(raw_temp, 1)).replace(".", "") + "c"
    pres = str(round(raw_pres))
    humi = str(round(raw_humi, 1)).replace(".", "") + "%"
    gas  = str(min(99, round(raw_gas / 1000))) + "ko"
    smoke = str(min(9999, raw_smoke))
    temp = temp.rjust(4)
    pres = pres.rjust(4)
    humi = humi.rjust(4)
    gas  = gas.rjust(4)
    smoke = smoke.rjust(4)
    return [temp, pres, humi, gas, smoke]

def calc_air_quality(humidity, gas):
    # calculate air quality where...
    # ideal humidity is 40% and contributes 25% to overall air quality
    # calculate humidity %age (min = 0%, max = 25%)
    target_hum = 40
    hum_percent = 25
    hum_diff = abs(target_hum - humidity)
    if humidity < target_hum:
        hum_percent = 25 - (hum_diff / target_hum * 25)
    if humidity > target_hum:
        hum_percent = 25 - (hum_diff / (100 - target_hum) * 25)
    
    # ideal gas readining is in excess of 50 kohms and contributes 75%
    # to overall air quality
    # calculate gas %age (min = 0%, max = 75%)
    max_gas = 50000
    gas = min(gas, max_gas)
    gas_diff = max_gas - gas
    gas_percent = 75 - (gas_diff / max_gas * 75)
    
    # add humidty % and gas % for overall quality reading
    air_quality = round(hum_percent + gas_percent,1)
    air_quality = min(air_quality, 99.9)
    return air_quality

def format_air(air_quality):
    # format reading to 4 character string including %
    air = str(air_quality).replace(".", "") + "%"
    return air

def publish_readings(readings):
    # publish readings to AWS IOT via MQTT connection
    message = {}
    message['time_stamp'] = datetime.now().strftime("%H:%M:%S")
    message['readings'] = readings
    messageJson = json.dumps(message)
    myAWSIoTMQTTClient.publish(topic, messageJson, 1)
    print('Published topic %s: %s\n' % (topic, messageJson))
    return

# =====================================================================
### Main function ############################

def main():
    display_index = 0
    tick = True
    name = display_names[display_index]
    decimal_point = 0
    draw_lcd(name, 0)
    sleep(1)
    drawn = False
    time_of_day = "day"
    while True:
        date_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for x in range(9):
            read_tb = read_trackball()
            # cycle to next name and reading when trackball pressed
            if read_tb == "sp":
                display_index += 1
                if display_index == 7:
                    display_index = 0
                name = display_names[display_index]
                draw_lcd(name, 0)
                sleep(0.9)
                break
            elif read_tb == "lp":
                raise KeyboardInterrupt
            sleep(0.1)
        
        # read raw data from sensors and calculate air quality
        readings = read_environment()
        humidity = readings[2]
        gas = readings[3]
        air_quality = calc_air_quality(humidity, gas)
        readings += [air_quality]
        
         # read data from max30105 particle sensor
        # !! this needs to be amended to be included in main readings data !!
        particles, temp = read_max30105()
        readings += [particles]
        
        
        # publish raw data from sensor readings to AWS
        if MQTT_broadcast == True:
            publish_readings(readings)
        
        # format the readings, store in a list and print to console
        air = format_air(air_quality)
        formatted_readings = [datetime.now().strftime("%H%M")]
        formatted_readings += format_readings(readings)
        formatted_readings += [air]
        print(date_stamp, display_names[display_index], formatted_readings)
        
        # set decimal point only on LED display for readings that need it
        # temperature, humidity and air quality
        if display_index in [2, 4, 5]:
            decimal_point = 0
        elif display_index in [1, 3, 6]:
            decimal_point = 1
            
        # flash decimal point when displaying time only
        if display_index == 0:
            if tick == True:
                decimal_point = 1
            else:
                decimal_point = 0
        tick = not tick 
        
        # display current formatted reading to LED display
        draw_lcd(formatted_readings[display_index], decimal_point)
        
        # change brightness of led matrix depending on time of day
        # dims display after 9pm and before 9am
        hour_now = datetime.now().hour
        if hour_now > 9 and  hour_now < 21 and time_of_day == "night":
            bright_lcd(True)
            time_of_day = "day"
        if hour_now > 21 and time_zone == "day":
            bright_lcd(False)
            time_of_day = "night"
        
        # set trackball LED to Red colour if any readings fall outside of range
        for index, reading in enumerate(readings):
            if reading < warnings[index][0] or reading > warnings[index][1]:
                warning = 1
                print("WARNING:", index, reading, warnings[index])
                break
            else:
                warning = 0
        if warning == 1:
            if tick == True:
                light_trackball(1)
            else:
                light_trackball(0)
        else:
            light_trackball(0)
        
       
    print("its not working")
    return 

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(e)
    except KeyboardInterrupt:
        # if keyboard interrupt then blank display
        display = LTP305(address=97)
        display.clear()
        display.show()
        display = LTP305(address=99)
        display.clear()
        display.show()
        light_trackball(0)
        max30105.set_slot_mode(1, 'off')
        max30105.set_slot_mode(2, 'off')
        max30105.set_slot_mode(3, 'off')
