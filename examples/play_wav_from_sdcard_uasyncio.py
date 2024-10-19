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
# uasyncio version

import os
import time
import urandom
import uasyncio as asyncio
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
WAV_FILE = "music-16k-16bits-stereo.wav"
WAV_SAMPLE_SIZE_IN_BITS = 16
FORMAT = I2S.STEREO
SAMPLE_RATE_IN_HZ = 16000
# ======= AUDIO CONFIGURATION =======


async def continuous_play(audio_out, wav):
    swriter = asyncio.StreamWriter(audio_out)

    _ = wav.seek(44)  # advance to first byte of Data section in WAV file

    # allocate sample array
    # memoryview used to reduce heap allocation
    wav_samples = bytearray(10000)
    wav_samples_mv = memoryview(wav_samples)

    # continuously read audio samples from the WAV file
    # and write them to an I2S DAC
    print("==========  START PLAYBACK ==========")

    while True:
        num_read = wav.readinto(wav_samples_mv)
        # end of WAV file?
        if num_read == 0:
            # end-of-file, advance to first byte of Data section
            _ = wav.seek(44)
        else:
            # apply temporary workaround to eliminate heap allocation in uasyncio Stream class.
            # workaround can be removed after acceptance of PR:
            #    https://github.com/micropython/micropython/pull/7868
            # swriter.write(wav_samples_mv[:num_read])
            swriter.out_buf = wav_samples_mv[:num_read]
            await swriter.drain()


async def another_task(name):
    while True:
        await asyncio.sleep(urandom.randrange(2, 5))
        print("{} woke up".format(name))
        time.sleep_ms(1)  # simulates task doing something


async def main(audio_out, wav):
    play = asyncio.create_task(continuous_play(audio_out, wav))
    task_a = asyncio.create_task(another_task("task a"))
    task_b = asyncio.create_task(another_task("task b"))

    # keep the event loop active
    while True:
        await asyncio.sleep_ms(10)


try:
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

    wav = open("/sd/{}".format(WAV_FILE), "rb")
    asyncio.run(main(audio_out, wav))
except (KeyboardInterrupt, Exception) as e:
    print("Exception {} {}\n".format(type(e).__name__, e))
finally:
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
    ret = asyncio.new_event_loop()  # Clear retained uasyncio state
    print("==========  DONE PLAYBACK ==========")
