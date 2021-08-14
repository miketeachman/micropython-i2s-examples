# The MIT License (MIT)
# Copyright (c) 2021 Mike Teachman
# https://opensource.org/licenses/MIT

# Purpose:  Play a pure audio tone out of a speaker or headphones
# 
# - write audio samples containing a pure tone to an I2S amplifier or DAC module
# - tone will play continuously in a loop until
#   a keyboard interrupt is detected or the board is reset
#
# Blocking version
# - the write() method blocks until the entire sample buffer is written to I2S

import os
import math
import struct
from machine import I2S
from machine import Pin

if os.uname().machine.find("PYBv1") == 0:
    
    # ======= I2S CONFIGURATION =======
    SCK_PIN = 'Y6'
    WS_PIN = 'Y5'  
    SD_PIN = 'Y8'
    I2S_ID = 2
    BUFFER_LENGTH_IN_BYTES = 10000
    # ======= I2S CONFIGURATION =======
    
elif os.uname().machine.find("PYBD") == 0:
    import pyb
    pyb.Pin("EN_3V3").on()  # provide 3.3V on 3V3 output pin
    
    # ======= I2S CONFIGURATION =======
    SCK_PIN = 'Y6'
    WS_PIN = 'Y5'  
    SD_PIN = 'Y8'
    I2S_ID = 2
    BUFFER_LENGTH_IN_BYTES = 10000
    # ======= I2S CONFIGURATION =======
    
elif os.uname().machine.find("ESP32") == 0:
    
    # ======= I2S CONFIGURATION =======
    SCK_PIN = 32
    WS_PIN = 25
    SD_PIN = 33
    I2S_ID = 0
    BUFFER_LENGTH_IN_BYTES = 10000
    # ======= I2S CONFIGURATION =======
    
else:
    print("Warning: program not tested with this board")

# ======= AUDIO CONFIGURATION =======
TONE_FREQUENCY_IN_HZ = 440
SAMPLE_SIZE_IN_BITS = 16
FORMAT = I2S.MONO  # only MONO supported in this example
SAMPLE_RATE_IN_HZ = 22050
# ======= AUDIO CONFIGURATION =======

audio_out = I2S(
    I2S_ID,
    sck=Pin(SCK_PIN),
    ws=Pin(WS_PIN),
    sd=Pin(SD_PIN),
    mode=I2S.TX,
    bits=SAMPLE_SIZE_IN_BITS,
    format=FORMAT,
    rate=SAMPLE_RATE_IN_HZ,
    ibuf=BUFFER_LENGTH_IN_BYTES,
)

# create a buffer containing the pure tone samples
samples_per_cycle = SAMPLE_RATE_IN_HZ // TONE_FREQUENCY_IN_HZ
sample_size_in_bytes = SAMPLE_SIZE_IN_BITS // 8
samples = bytearray(samples_per_cycle * sample_size_in_bytes)
volume_reduction_factor = 32
range = pow(2, SAMPLE_SIZE_IN_BITS) // 2 // volume_reduction_factor

if SAMPLE_SIZE_IN_BITS == 16:
    format = "<h"
else:  # assume 32 bits
    format = "<l"

for i in range(samples_per_cycle):
    sample = range + int((range - 1) * math.sin(2 * math.pi * i / samples_per_cycle))
    struct.pack_into(format, samples, i * sample_size_in_bytes, sample)

# continuously write tone sample buffer to an I2S DAC
print("==========  START PLAYBACK ==========")
try:
    while True:
        num_written = audio_out.write(samples)

except (KeyboardInterrupt, Exception) as e:
    print("caught exception {} {}".format(type(e).__name__, e))

# cleanup
audio_out.deinit()
print("Done")
