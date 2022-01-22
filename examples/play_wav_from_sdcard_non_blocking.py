# The MIT License (MIT)
# Copyright (c) 2022 Mike Teachman
# https://opensource.org/licenses/MIT

# Purpose:  Play a WAV audio file out of a speaker or headphones
#
# - read audio samples from a WAV file on SD Card
# - write audio samples to an I2S amplifier or DAC module
# - the WAV file will play continuously in a loop until
#   a keyboard interrupt is detected or the board is reset
#
# non-blocking version
# - the write() method is non-blocking.
# - a callback function is called when all sample data has been written to the I2S interface
# - a callback() method sets the callback function

import os
import time
import micropython
from machine import I2S
from machine import Pin

if os.uname().machine.count("PYBv1"):

    # ======= I2S CONFIGURATION =======
    SCK_PIN = "Y6"
    WS_PIN = "Y5"
    SD_PIN = "Y8"
    I2S_ID = 2
    BUFFER_LENGTH_IN_BYTES = 40000
    # ======= I2S CONFIGURATION =======

elif os.uname().machine.count("PYBD"):
    import pyb

    pyb.Pin("EN_3V3").on()  # provide 3.3V on 3V3 output pin
    os.mount(pyb.SDCard(), "/sd")

    # ======= I2S CONFIGURATION =======
    SCK_PIN = "Y6"
    WS_PIN = "Y5"
    SD_PIN = "Y8"
    I2S_ID = 2
    BUFFER_LENGTH_IN_BYTES = 40000
    # ======= I2S CONFIGURATION =======

elif os.uname().machine.count("ESP32"):
    from machine import SDCard

    sd = SDCard(slot=2)  # sck=18, mosi=23, miso=19, cs=5
    os.mount(sd, "/sd")

    # ======= I2S CONFIGURATION =======
    SCK_PIN = 32
    WS_PIN = 25
    SD_PIN = 33
    I2S_ID = 0
    BUFFER_LENGTH_IN_BYTES = 40000
    # ======= I2S CONFIGURATION =======

elif os.uname().machine.count("Raspberry"):
    from sdcard import SDCard
    from machine import SPI

    cs = Pin(13, machine.Pin.OUT)
    spi = SPI(
        1,
        baudrate=1_000_000,  # this has no effect on spi bus speed to SD Card
        polarity=0,
        phase=0,
        bits=8,
        firstbit=machine.SPI.MSB,
        sck=Pin(14),
        mosi=Pin(15),
        miso=Pin(12),
    )

    sd = SDCard(spi, cs)
    sd.init_spi(25_000_000)  # increase SPI bus speed to SD card
    os.mount(sd, "/sd")

    # ======= I2S CONFIGURATION =======
    SCK_PIN = 16
    WS_PIN = 17
    SD_PIN = 18
    I2S_ID = 0
    BUFFER_LENGTH_IN_BYTES = 40000
    # ======= I2S CONFIGURATION =======

elif os.uname().machine.count("MIMXRT"):
    from machine import SDCard

    sd = SDCard(1)  # Teensy 4.1: sck=45, mosi=43, miso=42, cs=44
    os.mount(sd, "/sd")

    # ======= I2S CONFIGURATION =======
    SCK_PIN = 4
    WS_PIN = 3
    SD_PIN = 2
    I2S_ID = 2
    BUFFER_LENGTH_IN_BYTES = 40000
    # ======= I2S CONFIGURATION =======

else:
    print("Warning: program not tested with this board")

# ======= AUDIO CONFIGURATION =======
WAV_FILE = "music-16k-16bits-mono.wav"
WAV_SAMPLE_SIZE_IN_BITS = 16
FORMAT = I2S.MONO
SAMPLE_RATE_IN_HZ = 16000
# ======= AUDIO CONFIGURATION =======

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
            _ = audio_out.write(silence)
            micropython.schedule(eof_callback, None)
        else:
            _ = audio_out.write(wav_samples_mv[:num_read])
    elif state == RESUME:
        state = PLAY
        _ = audio_out.write(silence)
    elif state == PAUSE:
        _ = audio_out.write(silence)
    elif state == STOP:
        # cleanup
        wav.close()
        if os.uname().machine.count("PYBD"):
            os.umount("/sd")
        elif os.uname().machine.count("ESP32"):
            os.umount("/sd")
            sd.deinit()
        elif os.uname().machine.count("Raspberry"):
            os.umount("/sd")
            spi.deinit()
        elif os.uname().machine.count("MIMXRT"):
            os.umount("/sd")
            sd.deinit()
        audio_out.deinit()
        print("Done")
    else:
        print("Not a valid state.  State ignored")


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

audio_out.irq(i2s_callback)
state = PAUSE

wav = open("/sd/{}".format(WAV_FILE), "rb")
_ = wav.seek(44)  # advance to first byte of Data section in WAV file

# allocate a small array of blank samples
silence = bytearray(1000)

# allocate sample array buffer
wav_samples = bytearray(10000)
wav_samples_mv = memoryview(wav_samples)

_ = audio_out.write(silence)

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
