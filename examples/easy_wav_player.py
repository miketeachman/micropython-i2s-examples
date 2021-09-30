# The MIT License (MIT)
# Copyright (c) 2021 Mike Teachman
# https://opensource.org/licenses/MIT
#
# Purpose:  Play a WAV audio file out of a speaker or headphones
#

import os
import time
from machine import Pin
from wavplayer import WavPlayer

if os.uname().machine.find("PYBv1") == 0:
    
    # ======= I2S CONFIGURATION =======
    SCK_PIN = 'Y6'
    WS_PIN = 'Y5'  
    SD_PIN = 'Y8'
    I2S_ID = 2
    BUFFER_LENGTH_IN_BYTES = 40000
    # ======= I2S CONFIGURATION =======
    
elif os.uname().machine.find("PYBD") == 0:
    import pyb
    pyb.Pin("EN_3V3").on()  # provide 3.3V on 3V3 output pin
    
    # ======= SD CARD CONFIGURATION =======
    os.mount(pyb.SDCard(), "/sd")
    # ======= SD CARD CONFIGURATION =======
    
    # ======= I2S CONFIGURATION =======
    SCK_PIN = 'Y6'
    WS_PIN = 'Y5'  
    SD_PIN = 'Y8'
    I2S_ID = 2
    BUFFER_LENGTH_IN_BYTES = 40000
    # ======= I2S CONFIGURATION =======
    
elif os.uname().machine.find("ESP32") == 0:
    from machine import SDCard
    
    # ======= SD CARD CONFIGURATION =======
    sd = SDCard(slot=2) # sck=18, mosi=23, miso=19, cs=5 
    os.mount(sd, "/sd")
    # ======= SD CARD CONFIGURATION =======
    
    # ======= I2S CONFIGURATION =======
    SCK_PIN = 32
    WS_PIN = 25
    SD_PIN = 33
    I2S_ID = 0
    BUFFER_LENGTH_IN_BYTES = 40000
    # ======= I2S CONFIGURATION =======
    
else:
    raise NotImplementedError("I2S protocol not supported on this board ")
    
wp = WavPlayer(id=I2S_ID, 
               sck_pin=Pin(SCK_PIN), 
               ws_pin=Pin(WS_PIN), 
               sd_pin=Pin(SD_PIN), 
               ibuf=BUFFER_LENGTH_IN_BYTES)

wp.play("music-16k-16bits-stereo.wav", loop=False)
# wait until the entire WAV file has been played
while wp.isplaying() == True:
    # other actions can be done inside this loop during playback
    pass
wp.play("music-16k-16bits-mono.wav", loop=False)
time.sleep(10)  # play for 10 seconds
wp.pause()
time.sleep(5)  # pause playback for 5 seconds
wp.resume() # continue playing to the end of the WAV file