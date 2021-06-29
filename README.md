# MicroPython I2S Examples

This repository provides MicroPython example code, showing how to use the I2S protocol with development boards supporting MicroPython.  The I2S protocol can be used to play WAV audio files through a speaker or headphone, or to record microphone audio to a WAV file on a SD card. 

The examples have been tested on 4 boards:  Pyboard D SF2W, Pyboard V1.1, ESP32, and ESP32 with PSRAM.  To use I2S with MicroPython you will need to make a custom MicroPython build and integrate [pull request](https://github.com/micropython/micropython/pull/7183) into the build.  Or, download and install one of the [pre-built firmware binaries](firmware)

The goal is to have this Pull Requests included in an official MicroPython release  

#### Pre-built Firmware Binaries
Pre-built firmware binaries based on the MicroPython V1.16 release are available in the [firmware](firmware) folder.  These binaries can be downloaded to a development board by following instructions posted at the [MicroPython download site](https://micropython.org/download/).

#### Boards Tested
  * Pyboard D SF2W
  * Pyboard V1.1
  * Adafruit Huzzah Feather ESP32 with external SD card
  * Lolin D32 Pro
  * Lolin D32 with external SD card
  * TinyPico with external SD card
  
#### I2S Microphone Boards Tested
 * INMP441 microphone module available on ebay, aliexpress, amazon
 * MSM261S4030H0 microphone module available on ebay, aliexpress, amazon
 * Adafruit I2S MEMS Microphone Breakout - SPH0645LM4H. See Workaround note below.
  
#### I2S DAC and Amplifier Boards Tested
   * Adafruit I2S 3W Class D Amplifier Breakout - MAX98357A
   * I2S PCM5102 Stereo DAC Decoder available on ebay, aliexpress, amazon
   * Wondom 2 x 30W Class D Audio Amplifier Board & DAC, based on TI TAS5756 device
   
#### Quick Start - play an audio tone through ear phones
The easiest way to get started with I2S is playing a pure tone to ear phones using a DAC board such as the I2S PCM5102 Stereo DAC Decoder board.  Here are the steps:

1. Decide what MicroPython development board pins will be used for the I2S signals SCK, WS, SD
1. Make the following wiring connections using a quality breadboard and jumper wires.  22 guage wire is often superior to commercially purchased jumpers.

    |PCM5102 board|MicroPython board|
    |--|--|
    |VIN|+3.3V|
    |GND|GND|
    |SCK|GND|
    |BCK|SCK pin|
    |LCK|WS pin|
    |DIN|SD pin|

1. Download the appropriate firmware that supports the I2S protocol into the MicroPython development board
1. Establish a REPL connection to the board
1. Load the example code `play-tone.py` into a text editor, found in the [examples](examples) folder
1. Configure the pins SCK, WS, SD, and I2S_ID.  Refer to the GPIO mappings section, below
1. Configure the tone frequency, bits per samples, sampling frequency
1. Copy the code e.g.  ctrl-A, ctrl-C
1. Ctrl-E in the REPL
1. Paste code into the REPL
1. Ctrl-D in the REPL to run the code
1. Result: the tone should play in the ear phones
1. Try different tone frequencies

#### Pyboard GPIO mappings for SCK, WS, SD

On Pyboard devices I2S compatible GPIO pins are mapped to a specific I2S hardware bus.  The tables below show this mapping.  For example, the GPIO pin "Y6" can only be used with I2S ID=2. 

Pyboard D with MicroPython WBUS-DIP28 adapter

|I2S ID|SCK|WS|SD|
|--|--|--|--|
|1|X6,W29|X5,W16|Y4|
|2|Y1,Y6,Y9|Y3,Y5|Y8,W24|

Pyboard V1.0/V1.1

|I2S ID|SCK|WS|SD|
|--|--|--|--|
|2|Y6,Y9|Y4,Y5|Y8,X22|

#### ESP32 GPIO mappings for SCK, WS, SD

All ESP32 GPIO pins can be used for I2S, with attention to special cases:
*   GPIO34 to GPIO39 are output-only
*   GPIO strapping pins:  see note below on using strapping pins

Strapping Pin consideration:
The following ESP32 GPIO strapping pins should be **used with caution**.  There is a risk that the state of the attached hardware can affect the boot sequence.  When possible, use other GPIO pins.
*   GPIO0 - used to detect boot-mode.  Bootloader runs when pin is low during powerup. Internal pull-up resistor.
*   GPIO2 - used to enter serial bootloader.  Internal pull-down resistor.
*   GPIO4 - technical reference indicates this is a strapping pin, but usage is not described.  Internal pull-down resistor.
*   GPIO5 - used to configure SDIO Slave.  Internal pull-up resistor.
*   GPIO12 - used to select flash voltage.  Internal pull-down resistor.
*   GPIO15 - used to configure silencing of boot messages.  Internal pull-up resistor.

### MicroPython examples
MicroPython example code is contained in the [examples](examples) folder.  WAV files used in the examples are contained in the [wav](wav) folder.  These examples have been tested with all binaries in the [firmware](firmware) folder.

Each example file has configuration parameters, marked with

`# ======= AUDIO CONFIGURATION =======`
and 
`# ======= I2S CONFIGURATION =======`

### Workaround for Adafruit I2S MEMS Microphone Breakout - SPH0645LM4H
This is a well designed breakout board based on the SPH0645LM4H microphone device. Users need to be aware that the SPH0645LM4H device implements non-standard Philips I2S timing.  When used with the ESP32, all audio samples coming from the I2S microphone are shifted to the left by one bit. This increases the sound level by 6dB. More details on this problem are outlined a [StreetSense project log](https://hackaday.io/project/162059-street-sense/log/160705-new-i2s-microphone).  
Workaround:  Use the static I2S class method `shift()` to right shift all samples that are read from the microphone.