# The MIT License (MIT)
# Copyright (c) 2022 Mike Teachman
# https://opensource.org/licenses/MIT

# Purpose:  Read audio samples from an I2S microphone and write to SD card
#
# - read 32-bit audio samples from I2S hardware, typically an I2S MEMS Microphone
# - convert 32-bit samples to specified bit size and format
# - write samples to a SD card file in WAV format
# - samples will be continuously written to the WAV file
#   for the specified amount of time
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
    BUFFER_LENGTH_IN_BYTES = 60000  # larger buffer to accommodate slow SD card driver
    # ======= I2S CONFIGURATION =======

elif os.uname().machine.count("MIMXRT"):
    from machine import SDCard

    sd = SDCard(1)  # Teensy 4.1: sck=45, mosi=43, miso=42, cs=44
    os.mount(sd, "/sd")

    # ======= I2S CONFIGURATION =======
    SCK_PIN = 21
    WS_PIN = 20
    SD_PIN = 8
    I2S_ID = 1
    BUFFER_LENGTH_IN_BYTES = 40000
    # ======= I2S CONFIGURATION =======

else:
    print("Warning: program not tested with this board")

# ======= AUDIO CONFIGURATION =======
WAV_FILE = "mic.wav"
RECORD_TIME_IN_SECONDS = 10
WAV_SAMPLE_SIZE_IN_BITS = 16
FORMAT = I2S.MONO
SAMPLE_RATE_IN_HZ = 22050
# ======= AUDIO CONFIGURATION =======

format_to_channels = {I2S.MONO: 1, I2S.STEREO: 2}
NUM_CHANNELS = format_to_channels[FORMAT]
WAV_SAMPLE_SIZE_IN_BYTES = WAV_SAMPLE_SIZE_IN_BITS // 8
RECORDING_SIZE_IN_BYTES = (
    RECORD_TIME_IN_SECONDS * SAMPLE_RATE_IN_HZ * WAV_SAMPLE_SIZE_IN_BYTES * NUM_CHANNELS
)


def create_wav_header(sampleRate, bitsPerSample, num_channels, num_samples):
    datasize = num_samples * num_channels * bitsPerSample // 8
    o = bytes("RIFF", "ascii")  # (4byte) Marks file as RIFF
    o += (datasize + 36).to_bytes(
        4, "little"
    )  # (4byte) File size in bytes excluding this and RIFF marker
    o += bytes("WAVE", "ascii")  # (4byte) File type
    o += bytes("fmt ", "ascii")  # (4byte) Format Chunk Marker
    o += (16).to_bytes(4, "little")  # (4byte) Length of above format data
    o += (1).to_bytes(2, "little")  # (2byte) Format type (1 - PCM)
    o += (num_channels).to_bytes(2, "little")  # (2byte)
    o += (sampleRate).to_bytes(4, "little")  # (4byte)
    o += (sampleRate * num_channels * bitsPerSample // 8).to_bytes(4, "little")  # (4byte)
    o += (num_channels * bitsPerSample // 8).to_bytes(2, "little")  # (2byte)
    o += (bitsPerSample).to_bytes(2, "little")  # (2byte)
    o += bytes("data", "ascii")  # (4byte) Data Chunk Marker
    o += (datasize).to_bytes(4, "little")  # (4byte) Data size in bytes
    return o


async def record_wav_to_sdcard(audio_in, wav):
    sreader = asyncio.StreamReader(audio_in)

    # create header for WAV file and write to SD card
    wav_header = create_wav_header(
        SAMPLE_RATE_IN_HZ,
        WAV_SAMPLE_SIZE_IN_BITS,
        NUM_CHANNELS,
        SAMPLE_RATE_IN_HZ * RECORD_TIME_IN_SECONDS,
    )
    num_bytes_written = wav.write(wav_header)

    # allocate sample array
    # memoryview used to reduce heap allocation
    mic_samples = bytearray(10000)
    mic_samples_mv = memoryview(mic_samples)

    num_sample_bytes_written_to_wav = 0

    # continuously read audio samples from I2S hardware
    # and write them to a WAV file stored on a SD card
    print("Recording size: {} bytes".format(RECORDING_SIZE_IN_BYTES))
    print("==========  START RECORDING ==========")
    while num_sample_bytes_written_to_wav < RECORDING_SIZE_IN_BYTES:
        # read samples from the I2S peripheral
        num_bytes_read_from_mic = await sreader.readinto(mic_samples_mv)
        # write samples to WAV file
        if num_bytes_read_from_mic > 0:
            num_bytes_to_write = min(
                num_bytes_read_from_mic, RECORDING_SIZE_IN_BYTES - num_sample_bytes_written_to_wav
            )
            num_bytes_written = wav.write(mic_samples_mv[:num_bytes_to_write])
            num_sample_bytes_written_to_wav += num_bytes_written

    print("==========  DONE RECORDING ==========")
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
    audio_in.deinit()


async def another_task(name):
    while True:
        await asyncio.sleep(urandom.randrange(2, 5))
        print("{} woke up".format(name))
        time.sleep_ms(10)  # simulates task doing something


async def main(audio_in, wav):
    play = asyncio.create_task(record_wav_to_sdcard(audio_in, wav))
    task_a = asyncio.create_task(another_task("task a"))
    task_b = asyncio.create_task(another_task("task b"))

    # keep the event loop active
    while True:
        await asyncio.sleep_ms(10)


try:
    audio_in = I2S(
        I2S_ID,
        sck=Pin(SCK_PIN),
        ws=Pin(WS_PIN),
        sd=Pin(SD_PIN),
        mode=I2S.RX,
        bits=WAV_SAMPLE_SIZE_IN_BITS,
        format=FORMAT,
        rate=SAMPLE_RATE_IN_HZ,
        ibuf=BUFFER_LENGTH_IN_BYTES,
    )

    wav = open("/sd/{}".format(WAV_FILE), "wb")
    asyncio.run(main(audio_in, wav))
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
    audio_in.deinit()
    ret = asyncio.new_event_loop()  # Clear retained uasyncio state
