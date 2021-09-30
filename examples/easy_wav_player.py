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
    
elif os.uname().machine.find("Raspberry") == 0:
    from sdcard import SDCard
    from machine import SPI
    cs = Pin(13, machine.Pin.OUT)
    spi = SPI(1,
              baudrate=1_000_000, # this has no effect on spi bus speed to SD Card
              polarity=0,
              phase=0,
              bits=8,
              firstbit=machine.SPI.MSB,
              sck=Pin(14),
              mosi=Pin(15),
              miso=Pin(12))
    
    sd = SDCard(spi, cs)
    sd.init_spi(25_000_000) # increase SPI bus speed to SD card
    vfs = os.VfsFat(sd)
    os.mount(vfs, "/sd")
    
    # ======= I2S CONFIGURATION =======
    SCK_PIN = 16
    WS_PIN = 17
    SD_PIN = 18
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