# The MIT License (MIT)
# Copyright (c) 2021 Mike Teachman
# https://opensource.org/licenses/MIT

# Purpose:  Play a WAV audio file out of a speaker or headphones
#
# - read audio samples from a WAV file on SD Card
# - write audio samples to an I2S amplifier or DAC module
# - the WAV file will play continuously in a loop until
#   a keyboard interrupt is detected or the board is reset
#
# Non-Blocking version
# - the write() method is non-blocking.
# - a callback function is called when all sample data has been written to the I2S interface
# - a callback() method sets the callback function

import uos
import time
import micropython
from machine import I2S
from machine import Pin

if uos.uname().machine.find("PYBv1") == 0:
    pass
elif uos.uname().machine.find("PYBD") == 0:
    import pyb
    pyb.Pin("EN_3V3").on()  # provide 3.3V on 3V3 output pin
    uos.mount(pyb.SDCard(), "/sd")
elif uos.uname().machine.find("ESP32") == 0:
    from machine import SDCard
    sd = SDCard(slot=3, sck=Pin(18), mosi=Pin(23), miso=Pin(19), cs=Pin(5))
    uos.mount(sd, "/sd")
else:
    print("Warning: program not tested with this board")
    
# ======= AUDIO CONFIGURATION =======
WAV_FILE = "music-16k-16bits-mono.wav"
WAV_SAMPLE_SIZE_IN_BITS = 16
FORMAT = I2S.MONO
SAMPLE_RATE_IN_HZ = 16000
# ======= AUDIO CONFIGURATION =======

# ======= I2S CONFIGURATION =======
SCK_PIN = "Y9"
WS_PIN = "Y4"
SD_PIN = "X22"
I2S_ID = 2
BUFFER_LENGTH_IN_BYTES = 40000
# ======= I2S CONFIGURATION =======

PLAY = 0
PAUSE = 1
RESUME = 2
STOP = 3

def eof_callback(arg):
    global state
    print("end of audio file")
    # state = STOP  # uncomment to stop looping playback


def i2s_callback(arg):
    global state
    if state == PLAY:
        num_read = wav.readinto(wav_samples_mv)
        # end of WAV file?
        if num_read == 0:
            # end-of-file, advance to first byte of Data section
            pos = wav.seek(44)
            num_written = audio_out.write(silence)
            micropython.schedule(eof_callback, None)
        else:
            num_written = audio_out.write(wav_samples_mv[:num_read])
    elif state == RESUME:
        state = PLAY
        num_written = audio_out.write(silence)
    elif state == PAUSE:
        num_written = audio_out.write(silence)
    elif state == STOP:
        # cleanup
        wav.close()
        if uos.uname().machine.find("PYBD") == 0:
            uos.umount("/sd")
        if uos.uname().machine.find("ESP32") == 0:
            uos.umount("/sd")
            sd.deinit()
        audio_out.deinit()
        print("Done")
    else:
        print("Not a valid state.  State ignored")


sck_pin = Pin(SCK_PIN)
ws_pin = Pin(WS_PIN)
sd_pin = Pin(SD_PIN)

audio_out = I2S(
    I2S_ID,
    sck=sck_pin,
    ws=ws_pin,
    sd=sd_pin,
    mode=I2S.TX,
    bits=WAV_SAMPLE_SIZE_IN_BITS,
    format=FORMAT,
    rate=SAMPLE_RATE_IN_HZ,
    ibuf=BUFFER_LENGTH_IN_BYTES,
)

audio_out.irq(i2s_callback)
state = PAUSE

wav = open("/sd/{}".format(WAV_FILE), "rb")
pos = wav.seek(44)  # advance to first byte of Data section in WAV file

# allocate a small array of blank samples
silence = bytearray(1000)

# allocate sample array buffer
wav_samples = bytearray(10000)
wav_samples_mv = memoryview(wav_samples)

num_written = audio_out.write(silence)

# add runtime code here ....
# changing 'state' will affect playback of audio file

print("starting playback for 10s")
state = PLAY
time.sleep(10)
print("pausing playback for 10s")
state = PAUSE
time.sleep(10)
print("resuming playback for 15s")
state = RESUME
time.sleep(15)
print("stopping playback")
state = STOP
