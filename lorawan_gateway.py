"""
Raspberry Pi Single Channel Gateway

Learn Guide: https://learn.adafruit.com/raspberry-pi-single-channel-lorawan-gateway
Author: Brent Rubell for Adafruit Industries
"""
# Import Python System Libraries
import json
import time
import subprocess
import uuid
# Import Adafruit Blinka Libraries
import busio
from digitalio import DigitalInOut, Direction, Pull
import board
# Import the SSD1306 module.
import adafruit_ssd1306

# Button A
btnA = DigitalInOut(board.D5)
btnA.direction = Direction.INPUT
btnA.pull = Pull.UP

# Button B
btnB = DigitalInOut(board.D6)
btnB.direction = Direction.INPUT
btnB.pull = Pull.UP

# Button C
btnC = DigitalInOut(board.D12)
btnC.direction = Direction.INPUT
btnC.pull = Pull.UP

# Create the I2C interface.
i2c = busio.I2C(board.SCL, board.SDA)

# 128x32 OLED Display
display = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c)
# Clear the display.
display.fill(0)
display.show()
width = display.width
height = display.height

# Gateway id calculation (based off MAC address)
mac_addr = hex(uuid.getnode()).replace('0x', '')
print('Gateway ID: {0}:{1}:{2}:ff:ff:{3}:{4}:{5}'.format(mac_addr[0:2],mac_addr[2:4],
                                                         mac_addr[4:6],mac_addr[6:8],
                                                         mac_addr[8:10], mac_addr[10:12]))

# Parse `global_conf.json`
with open('global_conf.json', 'r') as config:
    gateway_config = json.load(config)
# parse `SX127x_conf`
SX127x_conf = gateway_config['SX127x_conf']
gateway_freq = SX127x_conf['freq']/1000000
gateway_sf = SX127x_conf['spread_factor']
# parse `gateway_conf`
gateway_conf = gateway_config['gateway_conf']
gateway_name = gateway_conf['name']
# parse 'gateway_conf[servers]'
server_list = gateway_conf['servers']
ttn_server = server_list[0]
ttn_server_addr = ttn_server['address']

def stats():
    """Prints information about the Pi
    to a display
    """
    print('MODE: Pi Stats')
    # Clear Display
    display.fill(0)
    # Shell scripts for system monitoring from here :
    # https://unix.stackexchange.com/questions/119126/command-to-display-memory-usage-disk-usage-and-cpu-load
    cmd = "hostname -I | cut -d\' \' -f1"
    IP = subprocess.check_output(cmd, shell=True).decode("utf-8")
    cmd = "top -bn1 | grep load | awk '{printf \"CPU Load: %.2f\", $(NF-2)}'"
    CPU = subprocess.check_output(cmd, shell=True).decode("utf-8")
    cmd = "free -m | awk 'NR==2{printf \"Mem: %s/%s MB  %.2f%%\", $3,$2,$3*100/$2 }'"
    MemUsage = subprocess.check_output(cmd, shell=True).decode("utf-8")
    # write text to display
    display.text("IP: "+str(IP), 0, 0, 1)
    display.text(str(CPU), 0, 15, 1)
    display.text(str(MemUsage), 0, 25, 1)
    # display text for 3 seconds
    display.show()
    time.sleep(3)

def gateway():
    """Runs the single channel packet forwarder,
    sends output to a display.
    """
    print('MODE: Pi Gateway')
    # Clear Display
    display.fill(0)
    display.text("Starting Gateway...", 15, 0, 1)
    display.show()
    print('starting gateway...')
    try:
        proc = subprocess.Popen("./single_chan_pkt_fwd",
                                bufsize=-1, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        print("To run the single packet forwarder, you'll need to run `sudo make all` first.")
        return
    display.fill(0)
    display.text(gateway_name, 15, 0, 1)
    display.show()
    while True:
        new_line = proc.stdout.readline().decode('utf-8')
        print(new_line)
        # grab new data on gateway status update
        if new_line == "gateway status update\n":
            display.fill(0)
            gtwy_timestamp = proc.stdout.readline().decode('utf-8')
            print('time:', gtwy_timestamp)
            gtwy_status = proc.stdout.readline().decode('utf-8')
            print(gtwy_status)
            display.text(gateway_name, 15, 0, 1)
            display.text(gtwy_status, 0, 15, 1)
            display.text(gtwy_timestamp[11:23], 25, 25, 1)
        elif new_line == "incoming packet...\n":
            display.fill(0)
            print('incoming pkt...')
            # read incoming packet info
            pkt_json = proc.stdout.readline().decode('utf-8')
            # remove "gateway status update" text from TTN packet
            pkt_json = pkt_json.replace("gateway status update", "")
            print(pkt_json)
            # parse packet
            pkt_data = json.loads(pkt_json)
            rxpk_data = pkt_data['rxpk']
            pkt_data = rxpk_data.pop(0)
            # display packet info
            pkt_freq = pkt_data['freq']
            pkt_size = pkt_data['size']
            pkt_rssi = pkt_data['rssi']
            pkt_tmst = pkt_data['tmst']
            display.text('* PKT RX on {0}MHz'.format(pkt_freq), 0, 0, 1)
            display.text('RSSI: {0}dBm, Sz: {1}b'.format(pkt_rssi, pkt_size), 0, 10, 1)
            display.text('timestamp: {0}'.format(pkt_tmst), 0, 20, 1)
        display.show()

def gateway_info():
    """Displays information about the LoRaWAN gateway.
    """
    print('MODE: Gateway Info')
    display.fill(0)
    display.show()
    print('Server: ', ttn_server_addr[0:9])
    print('Freq: ', gateway_freq)
    print('SF: ', gateway_sf)
    print('Gateway Name:', gateway_name)
    # write 3 lines of text
    display.text(gateway_name, 15, 0, 1)
    display.text('{0} MHz, SF{1}'.format(gateway_freq, gateway_sf), 15, 10, 1)
    display.text('TTN: {0}'.format(ttn_server_addr[0:9]), 15, 20, 1)
    display.show()
    time.sleep(3)


while True:
    # draw a box to clear the image
    display.fill(0)
    display.text('LoRaWAN Gateway EUI', 15, 0, 1)
    display.text('{0}:{1}:{2}:ff'.format(mac_addr[0:2], mac_addr[2:4],
                                         mac_addr[4:6]), 25, 15, 1)
    display.text('ff:{0}:{1}:{2}'.format(mac_addr[6:8],mac_addr[8:10],
                                         mac_addr[10:12]), 25, 25, 1)

    # Radio Bonnet Buttons
    if not btnA.value:
        # show pi info
        stats()
    if not btnB.value:
        # start the gateway
        gateway()
    if not btnC.value:
        # show gateway configuration
        gateway_info()

    display.show()
    time.sleep(.1)
