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
# uasyncio version

import uos
import time
import urandom
import uasyncio as asyncio
from machine import I2S
from machine import Pin

if uos.uname().machine.find("PYBv1") == 0:
    pass
elif uos.uname().machine.find("PYBD") == 0:
    from pyb import SDCard
    pyb.Pin("EN_3V3").on()  # provide 3.3V on 3V3 output pin
    uos.mount(SDCard(), "/sd")
elif uos.uname().machine.find("ESP32") == 0:
    from machine import SDCard
    sd = SDCard(slot=3, sck=Pin(18), mosi=Pin(23), miso=Pin(19), cs=Pin(5))
    uos.mount(sd, "/sd")
else:
    print("Warning: program not tested with this board")

# ======= AUDIO CONFIGURATION =======
WAV_FILE = "music-16k-16bits-stereo.wav"
WAV_SAMPLE_SIZE_IN_BITS = 16
FORMAT = I2S.STEREO
SAMPLE_RATE_IN_HZ = 16000
# ======= AUDIO CONFIGURATION =======

# ======= I2S CONFIGURATION =======
SCK_PIN = 33
WS_PIN = 25
SD_PIN = 32
I2S_ID = 1
BUFFER_LENGTH_IN_BYTES = 40000
# ======= I2S CONFIGURATION =======


async def continuous_play(audio_out, wav):
    swriter = asyncio.StreamWriter(audio_out)

    pos = wav.seek(44)  # advance to first byte of Data section in WAV file

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
            pos = wav.seek(44)
        else:
            swriter.write(wav_samples_mv[:num_read])
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
        bufferlen=BUFFER_LENGTH_IN_BYTES,
    )

    wav = open("/sd/{}".format(WAV_FILE), "rb")
    asyncio.run(main(audio_out, wav))
except (KeyboardInterrupt, Exception) as e:
    print("Exception {} {}\n".format(type(e).__name__, e))
finally:
    # cleanup
    wav.close()
    if uos.uname().machine.find("PYBD") == 0:
        uos.umount("/sd")
    if uos.uname().machine.find("ESP32") == 0:
        uos.umount("/sd")
        sd.deinit()
    audio_out.deinit()
    ret = asyncio.new_event_loop()  # Clear retained uasyncio state
    print("==========  DONE PLAYBACK ==========")
