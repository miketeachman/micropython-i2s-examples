# The MIT License (MIT)
# Copyright (c) 2023 Mike Teachman
# https://opensource.org/licenses/MIT

# Purpose:  Play a WAV audio file using the Teensy Audio Shield, Rev D
#
# - read audio samples from a WAV file on SD Card
# - master clock is generated using the machine.PWM class
# - write audio samples to a SGTL5000 codec on the Teensy Audio Shield
# - the WAV file will play continuously in a loop until
#   a keyboard interrupt is detected or the board is reset
#
# blocking version
# - the write() method blocks until the entire sample buffer is written to the I2S interface
#
# Requires a MicroPython driver for the SGTL5000 codec.  Copy sgtl5000.py to the file system.
#   https://github.com/rdagger/micropython-sgtl5000
#
# This example code was tested on a Lolin D32 Pro ESP32 board, but can 
# be run on other boards with minor changes to SD card, I2C, and I2S pin assignments.
#   https://www.wemos.cc/en/latest/d32/d32_pro.html

import os
import time
from machine import PWM
from machine import I2C
from machine import I2S
from machine import Pin
from machine import SDCard
from sgtl5000 import CODEC

sd = SDCard(slot=2, cs=Pin(4))  # sck=18, mosi=23, miso=19, cs=4
os.mount(sd, "/sd")

# ======= I2S CONFIGURATION =======
SCK_PIN = 33
WS_PIN = 25
SD_PIN = 32
MCK_PIN = 5
I2S_ID = 1
BUFFER_LENGTH_IN_BYTES = 40000
# ======= I2S CONFIGURATION =======

# ======= AUDIO CONFIGURATION =======
WAV_FILE = "le-blues-de-la-vache-44k1-16bits-stereo.wav"
WAV_SAMPLE_SIZE_IN_BITS = 16
FORMAT = I2S.STEREO
SAMPLE_RATE_IN_HZ = 44100
# ======= AUDIO CONFIGURATION =======

audio_out = I2S(
    I2S_ID,
    sck=Pin(SCK_PIN),
    ws=Pin(WS_PIN),
    sd=Pin(SD_PIN),
    mode=I2S.TX,
    bits=WAV_SAMPLE_SIZE_IN_BITS,
    format=FORMAT,
    rate=SAMPLE_RATE_IN_HZ,
    ibuf=BUFFER_LENGTH_IN_BYTES,
)

# start the master clock, 50% duty cycle
# important note:  the SGTL5000 device must have a master clock *BEFORE* I2C will work
pwm = PWM(Pin(MCK_PIN), freq=SAMPLE_RATE_IN_HZ*256, duty_u16=32768)

# configure the SGTL5000 codec
i2c = I2C(0, sda=Pin(26), scl=Pin(27), freq=400000)
codec = CODEC(0x0A, i2c)
codec.mute_dac(False)
codec.dac_volume(0.9, 0.9)
codec.headphone_select(0)
codec.mute_headphone(False)
codec.volume(0.7, 0.7)

wav = open("/sd/{}".format(WAV_FILE), "rb")
_ = wav.seek(44)  # advance to first byte of Data section in WAV file

# allocate sample array
# memoryview used to reduce heap allocation
wav_samples = bytearray(10000)
wav_samples_mv = memoryview(wav_samples)

# continuously read audio samples from the WAV file
# and write them to an I2S DAC
print("==========  START PLAYBACK ==========")
try:
    while True:
        num_read = wav.readinto(wav_samples_mv)
        # end of WAV file?
        if num_read == 0:
            # end-of-file, advance to first byte of Data section
            _ = wav.seek(44)
        else:
            _ = audio_out.write(wav_samples_mv[:num_read])
except (KeyboardInterrupt, Exception) as e:
    print("caught exception {} {}".format(type(e).__name__, e))

# cleanup
wav.close()
os.umount("/sd")
sd.deinit()
audio_out.deinit()
print("Done")
