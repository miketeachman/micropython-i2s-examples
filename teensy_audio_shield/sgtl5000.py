"""
Library to control SGTL5000.

Ported to MicroPython by rdagger from Audio Library for Teensy 3.X:
    https:github.com/PaulStoffregen/Audio
    https://github.com/PaulStoffregen/Audio/blob/master/control_sgtl5000.cpp
The original code was written by Paul Stoffregen - Copyright (c) 2014

I2S Conventions
--------------------
    Bit Clock (BCLK) - serial clock SCK
    Word Clock (WS or word select) - Left-right Clock (LRCLK)
    Serial Data (SD) - SDATA, SDIN, SDOUT, DACDAT, ADCDAT, etc

"""
from math import cos, pi, sin, sqrt
from micropython import const  # type: ignore
from time import sleep, sleep_ms


class CODEC:
    """SGTL5000 audio codec controller."""

    CHIP_ID = const(0x0000)
    """15:8 PARTID 0xA0 - 8 bit identifier for SGTL5000
       7:0  REVID 0x00 - revision number for SGTL5000."""

    CHIP_DIG_POWER = const(0x0002)
    """6	ADC_POWERUP	1=Enable, 0=disable the ADC block, both digital & analog,
       5	DAC_POWERUP	1=Enable, 0=disable the DAC block, both analog and digital
       4	DAP_POWERUP	1=Enable, 0=disable the DAP block
       1	I2S_OUT_POWERUP	1=Enable, 0=disable the I2S data output
       0	I2S_IN_POWERUP	1=Enable, 0=disable the I2S data input"""

    CHIP_CLK_CTRL = const(0x0004)
    """5:4	RATE_MODE Sets the sample rate mode. MCLK_FREQ is still specified
            relative to the rate in SYS_FS
            0x0 = SYS_FS specifies the rate
            0x1 = Rate is 1/2 of the SYS_FS rate
            0x2 = Rate is 1/4 of the SYS_FS rate
            0x3 = Rate is 1/6 of the SYS_FS rate
        3:2	SYS_FS Sets the internal system sample rate (default=2)
            0x0 = 32 kHz
            0x1 = 44.1 kHz
            0x2 = 48 kHz
            0x3 = 96 kHz
        1:0	MCLK_FREQ Identifies incoming SYS_MCLK frequency and if the PLL
            should be used
            0x0 = 256*Fs
            0x1 = 384*Fs
            0x2 = 512*Fs
            0x3 = Use PLL
            The 0x3 (Use PLL) setting must be used if the SYS_MCLK is not
            a standard multiple of Fs (256, 384, or 512). This setting can
            also be used if SYS_MCLK is a standard multiple of Fs.
            Before this field is set to 0x3 (Use PLL), the PLL must be
            powered up by setting CHIP_ANA_POWER->PLL_POWERUP and
            CHIP_ANA_POWER->VCOAMP_POWERUP.  Also, the PLL dividers must
            be calculated based on the external MCLK rate and
            CHIP_PLL_CTRL register must be set (see CHIP_PLL_CTRL register
            description details on how to calculate the divisors)."""

    CHIP_I2S_CTRL = const(0x0006)
    """8	SCLKFREQ Sets frequency of I2S_SCLK when in master mode (MS=1).
            When in slave mode (MS=0), this field must be set appropriately
            to match SCLK input rate.
                0x0 = 64Fs
                0x1 = 32Fs - Not supported for RJ mode (I2S_MODE = 1)
       7	MS Configures master or slave of I2S_LRCLK and I2S_SCLK.
                0x0 = Slave: I2S_LRCLK an I2S_SCLK are inputs
                0x1 = Master: I2S_LRCLK and I2S_SCLK are outputs
                NOTE: If the PLL is used (CHIP_CLK_CTRL->MCLK_FREQ==0x3),
                the SGTL5000 must be a master of the I2S port (MS==1)
       6	SCLK_INV Sets the edge that data (input and output) is clocked
            in on for I2S_SCLK
                0x0 = data is valid on rising edge of I2S_SCLK
                0x1 = data is valid on falling edge of I2S_SCLK
       5:4	DLEN I2S data length (default=1)
                0x0 = 32 bits (only valid when SCLKFREQ=0), not valid for
                Right Justified Mode
                0x1 = 24 bits (only valid when SCLKFREQ=0)
                0x2 = 20 bits
                0x3 = 16 bits
       3:2	I2S_MODE Sets the mode for the I2S port
                0x0 = I2S mode or Left Justified (Use LRALIGN to select)
                0x1 = Right Justified Mode
                0x2 = PCM Format A/B
                0x3 = RESERVED
       1	LRALIGN I2S_LRCLK Alignment to data word. Not used for
            Right Justified mode
                0x0 = Data word starts 1 I2S_SCLK delay after
                I2S_LRCLK transition (I2S format, PCM format A)
                0x1 = Data word starts after I2S_LRCLK transition
                (left justified format, PCM format B)
       0	LRPOL I2S_LRCLK Polarity when data is presented.
                0x0 = I2S_LRCLK = 0 - Left, 1 - Right
                1x0 = I2S_LRCLK = 0 - Right, 1 - Left
                The left subframe should be presented first regardless of
                the setting of LRPOL."""

    CHIP_SSS_CTRL = const(0x000A)
    """14	DAP_MIX_LRSWAP DAP Mixer Input Swap
            0x0 = Normal Operation
            0x1 = Left and Right channels for the DAP MIXER Input are swapped.
       13	DAP_LRSWAP DAP Mixer Input Swap
            0x0 = Normal Operation
            0x1 = Left and Right channels for the DAP Input are swapped
       12	DAC_LRSWAP DAC Input Swap
            0x0 = Normal Operation
            0x1 = Left and Right channels for the DAC are swapped
       10	I2S_LRSWAP I2S_DOUT Swap
            0x0 = Normal Operation
            0x1 = Left and Right channels for the I2S_DOUT are swapped
       9:8	DAP_MIX_SELECT Select data source for DAP mixer
            0x0 = ADC
            0x1 = I2S_IN
            0x2 = Reserved
            0x3 = Reserved
       7:6	DAP_SELECT Select data source for DAP
            0x0 = ADC
            0x1 = I2S_IN
            0x2 = Reserved
            0x3 = Reserved
       5:4	DAC_SELECT Select data source for DAC (default=1)
            0x0 = ADC
            0x1 = I2S_IN
            0x2 = Reserved
            0x3 = DAP
       1:0	I2S_SELECT Select data source for I2S_DOUT
            0x0 = ADC
            0x1 = I2S_IN
            0x2 = Reserved
            0x3 = DAP"""

    CHIP_ADCDAC_CTRL = const(0x000E)
    """13	VOL_BUSY_DAC_RIGHT Volume Busy DAC Right
            0x0 = Ready
            0x1 = Busy - This indicates the channel has not reached its
            programmed volume/mute level
       12	VOL_BUSY_DAC_LEFT Volume Busy DAC Left
            0x0 = Ready
            0x1 = Busy - This indicates the channel has not reached its
            programmed volume/mute level
       9	VOL_RAMP_EN	Volume Ramp Enable (default=1)
            0x0 = Disables volume ramp. New volume settings take immediate
            effect without a ramp
            0x1 = Enables volume ramp
            This field affects DAC_VOL. The volume ramp effects both
            volume settings and mute When set to 1 a soft mute is enabled.
       8	VOL_EXPO_RAMP Exponential Volume Ramp Enable
            0x0 = Linear ramp over top 4 volume octaves
            0x1 = Exponential ramp over full volume range
            This bit only takes effect if VOL_RAMP_EN is 1.
       3	DAC_MUTE_RIGHT DAC Right Mute (default=1)
            0x0 = Unmute
            0x1 = Muted
            If VOL_RAMP_EN = 1, this is a soft mute.
       2	DAC_MUTE_LEFT DAC Left Mute (default=1)
            0x0 = Unmute
            0x1 = Muted
            If VOL_RAMP_EN = 1, this is a soft mute.
       1	ADC_HPF_FREEZE	ADC High Pass Filter Freeze
            0x0 = Normal operation
            0x1 = Freeze the ADC high-pass filter offset register.  The
            offset continues to be subtracted from the ADC data stream.
       0	ADC_HPF_BYPASS ADC High Pass Filter Bypass
            0x0 = Normal operation
            0x1 = Bypassed and offset not updated"""

    CHIP_DAC_VOL = const(0x0010)
    """15:8	DAC_VOL_RIGHT DAC Right Channel Volume.  Set the Right channel DAC
            volume with 0.5017 dB steps from 0 to -90 dB
            0x3B and less = Reserved
            0x3C = 0 dB
            0x3D = -0.5 dB
            0xF0 = -90 dB
            0xFC and greater = Muted
            If VOL_RAMP_EN = 1, there is an automatic ramp to the
            new volume setting.
       7:0	DAC_VOL_LEFT DAC Left Channel Volume.  Set the Left channel DAC
            volume with 0.5017 dB steps from 0 to -90 dB
            0x3B and less = Reserved
            0x3C = 0 dB
            0x3D = -0.5 dB
            0xF0 = -90 dB
            0xFC and greater = Muted
            If VOL_RAMP_EN = 1, there is an automatic ramp to the
            new volume setting."""

    CHIP_PAD_STRENGTH = const(0x0014)
    """9:8	I2S_LRCLK I2S LRCLK Pad Drive Strength (default=1)
            Sets drive strength for output pads per the table below.
            VDDIO    1.8 V     2.5 V     3.3 V
            0x0 = Disable
            0x1 =     1.66 mA   2.87 mA   4.02 mA
            0x2 =     3.33 mA   5.74 mA   8.03 mA
            0x3 =     4.99 mA   8.61 mA   12.05 mA
       7:6	I2S_SCLK I2S SCLK Pad Drive Strength (default=1)
       5:4	I2S_DOUT I2S DOUT Pad Drive Strength (default=1)
       3:2	CTRL_DATA I2C DATA Pad Drive Strength (default=3)
       1:0	CTRL_CLK I2C CLK Pad Drive Strength (default=3)
            (all use same table as I2S_LRCLK)"""

    CHIP_ANA_ADC_CTRL = const(0x0020)
    """8	ADC_VOL_M6DB ADC Volume Range Reduction
            This bit shifts both right and left analog ADC volume
            range down by 6.0 dB.
            0x0 = No change in ADC range
            0x1 = ADC range reduced by 6.0 dB
       7:4	ADC_VOL_RIGHT ADC Right Channel Volume
            Right channel analog ADC volume control in 1.5 dB steps.
            0x0 = 0 dB
            0x1 = +1.5 dB
            ...
            0xF = +22.5 dB
            This range is -6.0 dB to +16.5 dB if ADC_VOL_M6DB is set to 1.
       3:0	ADC_VOL_LEFT ADC Left Channel Volume
            (same scale as ADC_VOL_RIGHT)"""

    CHIP_ANA_HP_CTRL = const(0x0022)
    """14:8	HP_VOL_RIGHT Headphone Right Channel Volume  (default 0x18)
            Right channel headphone volume control with 0.5 dB steps.
            0x00 = +12 dB
            0x01 = +11.5 dB
            0x18 = 0 dB
            ...
            0x7F = -51.5 dB
       6:0	HP_VOL_LEFT	Headphone Left Channel Volume (default 0x18)
            (same scale as HP_VOL_RIGHT)"""

    CHIP_ANA_CTRL = const(0x0024)
    """8	MUTE_LO	LINEOUT Mute, 0 = Unmute, 1 = Mute  (default 1)
       6	SELECT_HP Select the headphone input, 0 = DAC, 1 = LINEIN
       5	EN_ZCD_HP Enable the headphone zero cross detector (ZCD)
            0x0 = HP ZCD disabled
            0x1 = HP ZCD enabled
       4	MUTE_HP	Mute the headphone outputs, 0 = Unmute, 1 = Mute (default)
       2	SELECT_ADC Select the ADC input, 0 = Microphone, 1 = LINEIN
       1	EN_ZCD_ADC Enable the ADC analog zero cross detector (ZCD)
            0x0 = ADC ZCD disabled
            0x1 = ADC ZCD enabled
       0	MUTE_ADC Mute the ADC analog volume, 0 = Unmute, 1 = Mute (default)"""

    CHIP_LINREG_CTRL = const(0x0026)
    """6	VDDC_MAN_ASSN Determines chargepump source when VDDC_ASSN_OVRD is set.
            0x0 = VDDA
            0x1 = VDDIO
       5	VDDC_ASSN_OVRD Charge pump Source Assignment Override
            0x0 = Charge pump source is automatically assigned based
            on higher of VDDA and VDDIO
            0x1 = the source of charge pump is manually assigned by
            VDDC_MAN_ASSN If VDDIO and VDDA are both the same
            and greater than 3.1 V, VDDC_ASSN_OVRD and
            VDDC_MAN_ASSN should be used to manually assign
            VDDIO as the source for charge pump.
       3:0	D_PROGRAMMING Sets the VDDD linear regulator output voltage in
            50 mV steps.  Must clear the LINREG_SIMPLE_POWERUP and
            STARTUP_POWERUP bits in the 0x0030 (CHIP_ANA_POWER) register after
            power-up, for this setting to produce the proper VDDD voltage.
            0x0 = 1.60
            0xF = 0.85"""

    CHIP_REF_CTRL = const(0x0028)  # bandgap reference bias voltage & currents
    """8:4	VAG_VAL	Analog Ground Voltage Control
            These bits control the analog ground voltage in 25 mV steps.
            This should usually be set to VDDA/2 or lower for best
            performance (maximum output swing at minimum THD). This VAG
            reference is also used for the DAC and ADC voltage reference.
            So changing this voltage scales the output swing of the DAC
            and the output signal of the ADC.
            0x00 = 0.800 V
            0x1F = 1.575 V
       3:1	BIAS_CTRL Bias control
            These bits adjust the bias currents for all of the analog
            blocks. By lowering the bias current a lower quiescent power
            is achieved. It should be noted that this mode can affect
            performance by 3-4 dB.
            0x0 = Nominal
            0x1-0x3=+12.5%
            0x4=-12.5%
            0x5=-25%
            0x6=-37.5%
            0x7=-50%
       0	SMALL_POP VAG Ramp Control
            Setting this bit slows down the VAG ramp from ~200 to ~400 ms
            to reduce the startup pop, but increases the turn on/off time.
            0x0 = Normal VAG ramp
            0x1 = Slow down VAG ramp"""

    CHIP_MIC_CTRL = const(0x002A)  # microphone gain & internal microphone bias
    """9:8	BIAS_RESISTOR MIC Bias Output Impedance Adjustment
            Controls an adjustable output impedance for the microphone bias.
            If this is set to zero the micbias block is powered off and
            the output is highZ.
            0x0 = Powered off
            0x1 = 2.0 kohm
            0x2 = 4.0 kohm
            0x3 = 8.0 kohm
       6:4	BIAS_VOLT MIC Bias Voltage Adjustment
            Controls an adjustable bias voltage for the microphone bias
            amp in 250 mV steps. This bias voltage setting should be no
            more than VDDA-200 mV for adequate power supply rejection.
            0x0 = 1.25 V
            ...
            0x7 = 3.00 V
       1:0	GAIN MIC Amplifier Gain
            Sets the microphone amplifier gain. At 0 dB setting the THD
            can be slightly higher than other paths- typically around
            ~65 dB. At other gain settings the THD are better.
            0x0 = 0 dB
            0x1 = +20 dB
            0x2 = +30 dB
            0x3 = +40 dB"""

    CHIP_LINE_OUT_CTRL = const(0x002C)
    """11:8	OUT_CURRENT	Controls the output bias current for the
            LINEOUT amplifiers.  The nominal recommended setting for a 10 kohm
            load with 1.0 nF load cap is 0x3. There are only 5 valid settings.
            0x0=0.18 mA
            0x1=0.27 mA
            0x3=0.36 mA
            0x7=0.45 mA
            0xF=0.54 mA
       5:0	LO_VAGCNTRL	LINEOUT Amplifier Analog Ground Voltage
            Controls the analog ground voltage for the LINEOUT amplifiers
            in 25 mV steps. This should usually be set to VDDIO/2.
            0x00 = 0.800 V
            ...
            0x1F = 1.575 V
            ...
            0x23 = 1.675 V
            0x24-0x3F are invalid"""

    CHIP_LINE_OUT_VOL = const(0x002E)
    """12:8	LO_VOL_RIGHT LINEOUT Right Channel Volume (default=4)
            Controls the right channel LINEOUT volume in 0.5 dB steps.
            Higher codes have more attenuation.
       4:0	LO_VOL_LEFT	LINEOUT Left Channel Output Level (default=4)
            Used to normalize the output level of the left line output
            to full scale based on the values used to set
            LINE_OUT_CTRL->LO_VAGCNTRL and CHIP_REF_CTRL->VAG_VAL.
            In general this field should be set to:
            40*log((VAG_VAL)/(LO_VAGCNTRL)) + 15
            Suggested values based on typical VDDIO and VDDA voltages.
            VDDA  VAG_VAL VDDIO  LO_VAGCNTRL LO_VOL_*
            1.8 V    0.9   3.3 V     1.55      0x06
            1.8 V    0.9   1.8 V      0.9      0x0F
            3.3 V   1.55   1.8 V      0.9      0x19
            3.3 V   1.55   3.3 V     1.55      0x0F
            After setting to the nominal voltage, this field can be used
            to adjust the output level in +/-0.5 dB increments by using
            values higher or lower than the nominal setting."""

    CHIP_ANA_POWER = const(0x0030)  # power down controls for analog blocks.
    """The only other power-down controls are BIAS_RESISTOR in the MIC_CTRL
       register and the EN_ZCD control bits in ANA_CTRL.
       14	DAC_MONO While DAC_POWERUP is set, this allows DAC to be put into
            left only mono operation for power savings.
            0=mono, 1=stereo (default)
       13	LINREG_SIMPLE_POWERUP Power up the simple (low power) digital
            supply regulator.  After reset, this bit can be cleared IF VDDD is
            driven externally OR the primary digital linreg is enabled with
            LINREG_D_POWERUP
       12	STARTUP_POWERUP	Power up the circuitry needed during the power up
            ramp and reset.  After reset this bit can be cleared if VDDD is
            coming from an external source.
       11	VDDC_CHRGPMP_POWERUP Power up the VDDC charge pump block. If neither
            VDDA or VDDIO is 3.0 V or larger this bit should be cleared before
            analog blocks are powered up.
       10	PLL_POWERUP	PLL Power Up, 0 = Power down, 1 = Power up
            When cleared, the PLL is turned off. This must be set before
            CHIP_CLK_CTRL->MCLK_FREQ is programmed to 0x3. The
            CHIP_PLL_CTRL register must be configured correctly before
            setting this bit.
       9	LINREG_D_POWERUP Power up the primary VDDD linear regulator,
            0 = Power down, 1 = Power up
       8	VCOAMP_POWERUP Power up the PLL VCO amplifier,
            0 = Power down, 1 = Power up
       7	VAG_POWERUP	Power up the VAG reference buffer.
            Setting this bit starts the power up ramp for the headphone
            and LINEOUT. The headphone (and/or LINEOUT) powerup should
            be set BEFORE clearing this bit. When this bit is cleared
            the power-down ramp is started. The headphone (and/or LINEOUT)
            powerup should stay set until the VAG is fully ramped down
            (200 to 400 ms after clearing this bit).
            0x0 = Power down, 0x1 = Power up
       6	ADC_MONO While ADC_POWERUP is set, this allows the ADC to be put into
            left only mono operation for power savings. This mode is useful
            when only using the microphone input.
            0x0 = Mono (left only), 0x1 = Stereo
       5	REFTOP_POWERUP Power up the reference bias currents
            0x0 = Power down, 0x1 = Power up
            This bit can be cleared when the part is a sleep state
            to minimize analog power.
       4	HEADPHONE_POWERUP Power up the headphone amplifiers
            0x0 = Power down, 0x1 = Power up
       3	DAC_POWERUP	Power up the DACs
            0x0 = Power down, 0x1 = Power up
       2	CAPLESS_HEADPHONE_POWERUP Power up the capless headphone mode
            0x0 = Power down, 0x1 = Power up
       1	ADC_POWERUP	Power up the ADCs
            0x0 = Power down, 0x1 = Power up
       0	LINEOUT_POWERUP	Power up the LINEOUT amplifiers
            0x0 = Power down, 0x1 = Power up"""

    CHIP_PLL_CTRL = const(0x0032)
    """15:11 INT_DIVISOR
       10:0 FRAC_DIVISOR"""

    CHIP_CLK_TOP_CTRL = const(0x0034)
    """11	ENABLE_INT_OSC Setting this bit enables an internal oscillator to be
            used for the zero cross detectors, the short detect recovery, and
            the charge pump. This allows the I2S clock to be shut off while
            still operating an analog signal path. This bit can be kept
            on when the I2S clock is enabled, but the I2S clock is more
            accurate so it is preferred to clear this bit when I2S is present.
       3	INPUT_FREQ_DIV2	SYS_MCLK divider before PLL input
            0x0 = pass through
            0x1 = SYS_MCLK is divided by 2 before entering PLL
            This must be set when the input clock is above 17 Mhz. This
            has no effect when the PLL is powered down."""

    CHIP_ANA_STATUS = const(0x0036)
    """9	LRSHORT_STS	This bit is high whenever a short is detected on the left
            or right channel headphone drivers.
       8	CSHORT_STS This bit is high whenever a short is detected on the
            capless headphone common/center channel driver.
       4	PLL_IS_LOCKED This bit goes high after the PLL is locked."""

    CHIP_ANA_TEST1 = const(0x0038)  # intended only for debug.
    CHIP_ANA_TEST2 = const(0x003A)  # intended only for debug.

    CHIP_SHORT_CTRL = const(0x003C)
    """14:12 LVLADJR Right channel headphone short detector in 25 mA steps.
            0x3=25 mA
            0x2=50 mA
            0x1=75 mA
            0x0=100 mA
            0x4=125 mA
            0x5=150 mA
            0x6=175 mA
            0x7=200 mA
            This trip point can vary by ~30% over process so leave plenty
            of guard band to avoid false trips.  This short detect trip
            point is also effected by the bias current adjustments made
            by CHIP_REF_CTRL->BIAS_CTRL and by CHIP_ANA_TEST1->HP_IALL_ADJ.
       10:8	LVLADJL Left channel headphone short detector in 25 mA steps.
            (same scale as LVLADJR)
       6:4	LVLADJC Capless headphone center channel short detector
            in 50 mA steps.
            0x3=50 mA
            0x2=100 mA
            0x1=150 mA
            0x0=200 mA
            0x4=250 mA
            0x5=300 mA
            0x6=350 mA
            0x7=400 mA
       3:2	MODE_LR	Behavior of left/right short detection
            0x0 = Disable short detector, reset short detect latch,
                software view non-latched short signal
            0x1 = Enable short detector and reset the latch at timeout
                (every ~50 ms)
            0x2 = This mode is not used/invalid
            0x3 = Enable short detector with only manual reset (have
                to return to 0x0 to reset the latch)
       1:0	MODE_CM	Behavior of capless headphone central short detection
            (same settings as MODE_LR)"""

    DAP_CONTROL = const(0x0100)
    DAP_PEQ = const(0x0102)
    DAP_BASS_ENHANCE = const(0x0104)
    DAP_BASS_ENHANCE_CTRL = const(0x0106)
    DAP_AUDIO_EQ = const(0x0108)
    DAP_SGTL_SURROUND = const(0x010A)
    DAP_FILTER_COEF_ACCESS = const(0x010C)
    DAP_COEF_WR_B0_MSB = const(0x010E)
    DAP_COEF_WR_B0_LSB = const(0x0110)
    DAP_AUDIO_EQ_BASS_BAND0 = const(0x0116)  # 115 Hz
    DAP_AUDIO_EQ_BAND1 = const(0x0118)  # 330 Hz
    DAP_AUDIO_EQ_BAND2 = const(0x011A)  # 990 Hz
    DAP_AUDIO_EQ_BAND3 = const(0x011C)  # 3000 Hz
    DAP_AUDIO_EQ_TREBLE_BAND4 = const(0x011E)  # 9900 Hz
    DAP_MAIN_CHAN = const(0x0120)
    DAP_MIX_CHAN = const(0x0122)
    DAP_AVC_CTRL = const(0x0124)
    DAP_AVC_THRESHOLD = const(0x0126)
    DAP_AVC_ATTACK = const(0x0128)
    DAP_AVC_DECAY = const(0x012A)
    DAP_COEF_WR_B1_MSB = const(0x012C)
    DAP_COEF_WR_B1_LSB = const(0x012E)
    DAP_COEF_WR_B2_MSB = const(0x0130)
    DAP_COEF_WR_B2_LSB = const(0x0132)
    DAP_COEF_WR_A1_MSB = const(0x0134)
    DAP_COEF_WR_A1_LSB = const(0x0136)
    DAP_COEF_WR_A2_MSB = const(0x0138)
    DAP_COEF_WR_A2_LSB = const(0x013A)

    SGTL5000_I2C_ADDR_CS_LOW = const(0x0A)  # CTRL_ADR0_CS pin low (normal)
    SGTL5000_I2C_ADDR_CS_HIGH = const(0x2A)  # CTRL_ADR0_CS  pin high

    # Filter Types
    FILTER_LOPASS = const(0x0)
    FILTER_HIPASS = const(0x1)
    FILTER_BANDPASS = const(0x2)
    FILTER_NOTCH = const(0x3)
    FILTER_PARAEQ = const(0x4)
    FILTER_LOSHELF = const(0x5)
    FILTER_HISHELF = const(0x6)

    # Frequency Adjustments
    FLAT_FREQUENCY = const(0x0)
    PARAMETRIC_EQUALIZER = const(0x1)
    TONE_CONTROLS = const(0x2)
    GRAPHIC_EQUALIZER = const(0x3)

    AUDIO_INPUT_LINEIN = const(0)
    AUDIO_INPUT_MIC = const(1)
    AUDIO_HEADPHONE_DAC = const(0)
    AUDIO_HEADPHONE_LINEIN = const(1)

    def __init__(self, address, i2c, mclk=11289600, fs=1):
        """Constructor for SGTL5000.

        Args:
            address(byte): Device I²C address (0x20 or 0x21)
            i2c (Class I2C):  I²C interface (Python & MicroPython compatible)
            mclk (int): Master clock frequency 11.2896 MHz Default
            fs (int): Sampling frequency
                      0=32 kHz
                      1=44.1 kHz Default
                      2=48 kHz
                      3=96 kHz
        Note:
            mclk (11.2896 MHz) = fs (44.1K) * 256
        """
        if not 0 <= fs <= 3:
            raise ValueError("Invalid sampling frequency value.")
        self.i2c = i2c
        self.address = address

        # VDDD is externally driven with 1.8V
        self.write_word(self.CHIP_ANA_POWER, 0x4060)
        # VDDA & VDDIO both over 3.1V
        self.write_word(self.CHIP_LINREG_CTRL, 0x006C)
        # VAG=1.575, normal ramp, +12.5% bias current
        self. write_word(self.CHIP_REF_CTRL, 0x01F2)
        # LO_VAGCNTRL=1.65V, OUT_CURRENT=0.54mA
        self.write_word(self.CHIP_LINE_OUT_CTRL, 0x0F22)
        # Allow up to 125mA
        self.write_word(self.CHIP_SHORT_CTRL, 0x4446)
        
        # Mute line out, head phone out & ADC
        #self.analog_ctrl = 0x0137
        #self.write_word(self.CHIP_ANA_CTRL, self.analog_ctrl)
        #sleep(.1)
        
        # SGTL is I2S Slave (power up: lineout, hp, adc, dac)
        self.write_word(self.CHIP_ANA_POWER, 0x40FF)
        # Power up all digital stuff
        self.write_word(self.CHIP_DIG_POWER, 0x0073)
        sleep_ms(400)
        # Default approx 1.3 volts peak-to-peak
        self.write_word(self.CHIP_LINE_OUT_VOL, 0x1D1D)
        # Fs=44.1 kHz, Fmclk=256*Fs
        self.write_word(self.CHIP_CLK_CTRL, 0x0004)
        # Fsclk=Fs*64, 32bit samples, I2S format (data length)
        self.write_word(self.CHIP_I2S_CTRL, 0x0030)
        # ADC->I2S, I2S->DAC
        self.write_word(self.CHIP_SSS_CTRL, 0x0010)
        # Unmute DAC, ADC normal operations, disable volume ramp
        self.adc_dac_ctrl = 0x0000
        self.write_word(self.CHIP_ADCDAC_CTRL, self.adc_dac_ctrl)
        # Digital gain, 0dB
        self.write_word(self.CHIP_DAC_VOL, 0x3C3C)
        # Set volume (lowest level)
        self.write_word(self.CHIP_ANA_HP_CTRL, 0x7F7F)
        # Enable & mute headphone output, select & unmute line in & enable ZCD
        self.analog_ctrl = 0x0036
        self.write_word(self.CHIP_ANA_CTRL, self.analog_ctrl)

    def adc_high_pass_filter(self, enable=True, freeze=False):
        """Enable or disable the ADC high-pass filter.
        Args:
            enable (bool): True=enable (default), False=disable
            freeze (bool): True=Freeze ADC high-pass filter offset register.
                           The offset continues to be subtracted from the ADC
                           data stream.
                           False=Normal operations."""
        if enable:
            self.adc_dac_ctrl &= ~(3)
        elif freeze:
            self.adc_dac_ctrl = (self.adc_dac_ctrl & ~3) | 2
        else:
            self.adc_dac_ctrl = (self.adc_dac_ctrl & ~3) | 1
        self.write_word(self.CHIP_ADCDAC_CTRL, self.adc_dac_ctrl)

    def audio_processor(self, enable=True, pre=True):
        """Enable or disable the audio processor.
        Args:
            enable (bool): True=enable (default),
                           False=disable ADC->I2S, I2S->DAC
            pre (bool): True=Pre-processor ADC->DAP, DAP->I2S, I2S->DAC
                        False=Post-processor ADC->I2S, I2S->DAP, DAP->DAC"""
        if not enable:
            # Disable audio processor
            self.write_word(self.CHIP_SSS_CTRL, 0x10)
            self.write_word(self.DAP_CONTROL, 0x00)
        elif pre:
            # Audio processor pre-processes analog input before microcontroller
            self.write_word(self.CHIP_SSS_CTRL, 0x13)
            self.write_word(self.DAP_CONTROL, 0x01)
        else:
            # Audio processor post-processes microcontroller output
            self.write_word(self.CHIP_SSS_CTRL, 0x70)
            self.write_word(self.DAP_CONTROL, 0x01)

    def auto_volume_configure(self, max_gain, lbi_response, hard_limit,
                              threshold, attack, decay):
        """Configure auto volume control
        Args:
            max_gain (int): 0=0 dB
                            1=6 dB
                            2=12 dB
            lbi_response (int): 0=0 ms
                                1=25 ms
                                2=50 ms
                                3=100 ms
            hard_limit (int): 0=Disabled (AVC compressor/expander enabled)
                              1=Enabled (Limited to programmed threshold,
                                         signal saturates at the threshold)
            threshold (float): 0 to -96 dB
            attack (float): Figure is dB/s rate at which gain is increased.
            decay (float): Figure is dB/s rate at which gain is decreased.
        """
        if not 0 <= max_gain <= 2:
            raise ValueError("Invalid max_gain value.")
        if not 0 <= lbi_response <= 3:
            raise ValueError("Invalid lbi_response value.")
        if not 0 <= hard_limit <= 1:
            raise ValueError("Invalid hard_limit value.")

        thresh = (pow(10, threshold / 20) * 0.636) * pow(2, 15)
        att = (1 - pow(10, -(attack / (20 * 44100)))) * pow(2, 19)
        dec = (1 - pow(10, -(decay / (20 * 44100)))) * pow(2, 23)
        self.write_word(self.DAP_AVC_THRESHOLD, thresh)
        self.write_word(self.DAP_AVC_ATTACK, att)
        self.write_word(self.DAP_AVC_DECAY, dec)
        self.auto_volume_control |= ((max_gain << 12) | (lbi_response << 8) |
                                     (hard_limit << 5))
        self.write_word(self.DAP_AVC_CTRL, self.auto_volume_control)

    def auto_volume_enable(self, enable=True):
        """Enable/disable auto volume control.
        Args:
            enable(bool): True=enable (default)
                          False=disable
        """
        if enable:
            self.auto_volume_control |= 1
        else:
            self.auto_volume_control &= ~1
        self.write_word(self.DAP_AVC_CTRL, self.auto_volume_control)

    def bass_enhance_configure(self, lr_level=5, bass_level=31, bypass_hpf=0,
                               cutoff=4):
        """Configure bass enhance.
        Args:
            lr_level (int): Left/Right mix level control
                            0=+6.0 dB for Main Channel
                            63= Least L/R Channel Level
            bass_level (int): Bass harmonic level control
                              0= Most harmonic boost
                              127=Least harmonic boost
            bypass_hpf (int): Bypass high pass filter
                              0=Enable high pass filter
                              1=Bypass high pass filter
            cutoff (int): Set cut-off frequency
                          0 = 80 Hz
                          1 = 100 Hz
                          2 = 125 Hz
                          3 = 150 Hz
                          4 = 175 Hz
                          5 = 200 Hz
                          6 = 225 Hz"""
        if not 0 <= lr_level <= 63:
            raise ValueError("Invalid lr_level value.")
        if not 0 <= bass_level <= 127:
            raise ValueError("Invalid bass_level value.")
        if not 0 <= bypass_hpf <= 1:
            raise ValueError("Invalid bypass_hpf value.")
        if not 0 <= cutoff <= 6:
            raise ValueError("Invalid cutoff value.")

        self.write_word(self.DAP_BASS_ENHANCE_CTRL,
                        ((0x3F - self.calc_volume(lr_level, 0x3F)) << 8) |
                        (0x7F - self.calc_volume(bass_level)))

        self.bass_enhance |= ((bypass_hpf << 8) | (cutoff << 4))
        self.write_word(self.DAP_BASS_ENHANCE, self.bass_enhance)

    def bass_enhance_enable(self, enable=True):
        """Enable/disable bass enhance.
        Args:
            enable(bool): True=enable (default)
                          False=disable
        """
        if enable:
            self.bass_enhance |= 1
        else:
            self.bass_enhance &= ~1
        self.write_word(self.DAP_BASS_ENHANCE, self.bass_enhance)

    def calc_biquad(self, filter_type, fc, db_gain, q, quantization_unit, fs):
        """Calculate biquadratic filter.
        Args:
            filter_type (int): Filter type 0 - 6 (see filter type constants)
            fc (float): Cutoff of center frequency
            db_gain (float): Gain (dB)
            q (float): Quality factor
            quantization_unit (int): Quantization unit
            fs (int): Sample frequency
        Returns:
            List(int) of coefficients
        Notes:
            Based on code from https://www.w3.org/TR/audio-eq-cookbook/
            SGTL5000_PEQ: quantization_unit=524288
            AudioFilterBiquad: quantization_unit=2147483648
            This filter has limits. Before calling routine with varying values
            please check that those values are limited to valid results."""

        a = 0.0
        if filter_type < self.FILTER_PARAEQ:
            a = pow(10, db_gain / 20)
        else:
            a = pow(10, db_gain / 40)
        w0 = 2.0 * pi * fc / fs
        cosw = cos(w0)
        sinw = sin(w0)
        alpha = sinw / (2 * q)
        beta = sqrt(a) / q
        a0 = a1 = a2 = b0 = b1 = b2 = 0.0

        if filter_type == self.FILTER_LOPASS:
            b0 = (1.0 - cosw) * 0.5
            b1 = 1.0 - cosw
            b2 = (1.0 - cosw) * 0.5
            a0 = 1.0 + alpha
            a1 = 2.0 * cosw
            a2 = alpha - 1.0
        elif filter_type == self.FILTER_HIPASS:
            b0 = (1.0 + cosw) * 0.5
            b1 = -(cosw + 1.0)
            b2 = (1.0 + cosw) * 0.5
            a0 = 1.0 + alpha
            a1 = 2.0 * cosw
            a2 = alpha - 1.0
        elif filter_type == self.FILTER_BANDPASS:
            b0 = alpha
            b1 = 0.0
            b2 = -alpha
            a0 = 1.0 + alpha
            a1 = 2.0 * cosw
            a2 = alpha - 1.0
        elif filter_type == self.FILTER_NOTCH:
            b0 = 1.0
            b1 = -2.0 * cosw
            b2 = 1.0
            a0 = 1.0 + alpha
            a1 = 2.0 * cosw
            a2 = -(1.0 - alpha)
        elif filter_type == self.FILTER_PARAEQ:
            b0 = 1.0 + (alpha * a)
            b1 = -2.0 * cosw
            b2 = 1.0 - (alpha * a)
            a0 = 1.0 + (alpha / a)
            a1 = 2.0 * cosw
            a2 = -(1.0 - (alpha / a))
        elif filter_type == self.FILTER_LOSHELF:
            b0 = a * ((a + 1.0) - ((a - 1.0) * cosw) + (beta * sinw))
            b1 = 2.0 * a * ((a - 1.0) - ((a + 1.0) * cosw))
            b2 = a * ((a + 1.0) - ((a - 1.0) * cosw) - (beta * sinw))
            a0 = (a + 1.0) + ((a - 1.0) * cosw) + (beta * sinw)
            a1 = 2.0 * ((a - 1.0) + ((a + 1.0) * cosw))
            a2 = -((a + 1.0) + ((a - 1.0) * cosw) - (beta * sinw))
        elif filter_type == self.FILTER_HISHELF:
            b0 = a * ((a + 1.0) + ((a - 1.0) * cosw) + (beta * sinw))
            b1 = -2.0 * a * ((a - 1.0) + ((a + 1.0) * cosw))
            b2 = a * ((a + 1.0) + ((a - 1.0) * cosw) - (beta * sinw))
            a0 = (a + 1.0) - ((a - 1.0) * cosw) + (beta * sinw)
            a1 = -2.0 * ((a - 1.0) - ((a + 1.0) * cosw))
            a2 = -((a + 1.0) - ((a - 1.0) * cosw) - (beta * sinw))
        else:
            b0 = 0.5
            b1 = 0.0
            b2 = 0.0
            a0 = 1.0
            a1 = 0.0
            a2 = 0.0

        a0 = (a0 * 2) / quantization_unit  # Once here instead of five times
        b0 /= a0
        coef = []
        coef.append(int(b0 + 0.499))
        b1 /= a0
        coef.append(int(b1 + 0.499))
        b2 /= a0
        coef.append(int(b2 + 0.499))
        a1 /= a0
        coef.append(int(a1 + 0.499))
        a2 /= a0
        coef.append(int(a2 + 0.499))
        return coef

    def calc_volume(self, volume, range=0x7f):
        """Converts 0:1 volume value to 0:range value.

        Args:
            volume(float): volume value between 0 and 1.
            range(integer): volume range (default 0x07)
        """
        cvol = int((volume * float(range)) + 0.499)
        if cvol > range:
            return range
        else:
            return cvol

    def dac_volume(self, left, right):
        """Set DAC left and right channel volume.
        Args:
            left (float): left channel DAC volume 0 (mute) to 1 (full)
            right (float): right channel DAC volume 0 (mute) to 1 (full)
        """
        if not 0 <= left <= 1 and not 0 <= right <= 1:
            raise ValueError("Invalid DAC volume values.")
        volume = (((0xFC - self.calc_volume(right, 0xC0)) << 8) |
                  (0xFC - self.calc_volume(left, 0xC0)))
        self.write_word(self.CHIP_DAC_VOL, volume)

    def dac_volume_ramp(self, enable=True, linear=False):
        """Enable or disable the DAC volume ramp.
        Args:
            enable (bool): True=enable (default), False=disable
            linear (bool): True=Linear ramp over top 4 volume octaves,
                False=Exponential ramp over full volume range (default)"""
        if enable:
            if linear:
                self.adc_dac_ctrl |= (1 << 9)
                self.adc_dac_ctrl &= ~(1 << 8)
            else:
                self.adc_dac_ctrl |= (3 << 8)
        else:
            self.adc_dac_ctrl &= ~(3 << 8)
        self.write_word(self.CHIP_ADCDAC_CTRL, self.adc_dac_ctrl)

    def headphone_select(self, input):
        """Select the headphone input.
        Args:
            input (int): 0=DAC, 1=Line In
        """
        if not 0 <= input <= 1:
            raise ValueError("Invalid headphone input value.")

        if input == self.AUDIO_HEADPHONE_DAC:
            self.analog_ctrl &= ~(1 << 6)
        elif input == self.AUDIO_HEADPHONE_LINEIN:
            self.analog_ctrl |= (1 << 6)
        self.write_word(self.CHIP_ANA_CTRL, self.analog_ctrl)

    def input_select(self, input):
        """Select the audio input.
        Args:
            input (int): 0=Line In, 1=Mic
        """
        if not 0 <= input <= 1:
            raise ValueError("Invalid audio input value.")

        if input == self.AUDIO_INPUT_LINEIN:
            self.write_word(self.CHIP_ANA_ADC_CTRL, 0x55)
            self.analog_ctrl |= (1 << 2)
            self.write_word(self.CHIP_ANA_CTRL, self.analog_ctrl)

        elif input == self.AUDIO_INPUT_MIC:
            self.write_word(self.CHIP_ANA_ADC_CTRL, 0x88)
            self.analog_ctrl &= ~(1 << 2)
            self.write_word(self.CHIP_ANA_CTRL, self.analog_ctrl)
            self.write_word(self.CHIP_MIC_CTRL, 0x173)

    def linein_level(self, left, right):
        """Set left and right channel linein level.
        Args:
            left (int): left channel level 0 - 15
            right (int): right channel level 0 - 15
        Notes:
            Measured full-scale peak-to-peak sine wave input for max signal
            0: 3.12 Volts p-p
            1: 2.63 Volts p-p
            2: 2.22 Volts p-p
            3: 1.87 Volts p-p
            4: 1.58 Volts p-p
            5: 1.33 Volts p-p
            6: 1.11 Volts p-p
            7: 0.94 Volts p-p
            8: 0.79 Volts p-p
            9: 0.67 Volts p-p
            10: 0.56 Volts p-p
            11: 0.48 Volts p-p
            12: 0.40 Volts p-p
            13: 0.34 Volts p-p
            14: 0.29 Volts p-p
            15: 0.24 Volts p-p
            """
        if not 0 <= left <= 15 and not 0 <= right <= 15:
            raise ValueError("Invalid linein level values.")
        self.write_word(self.CHIP_ANA_ADC_CTRL, (left << 4) | right)

    def lineout_level(self, left, right):
        """Set left and right channel lineout level.
        Args:
            left (int): left channel level 13 - 31
            right (int): right channel level 13-31
        Notes:
            Actual measured full-scale peak-to-peak sine wave output voltage:
            0-12: output has clipping
            13: 3.16 Volts p-p
            14: 2.98 Volts p-p
            15: 2.83 Volts p-p
            16: 2.67 Volts p-p
            17: 2.53 Volts p-p
            18: 2.39 Volts p-p
            19: 2.26 Volts p-p
            20: 2.14 Volts p-p
            21: 2.02 Volts p-p
            22: 1.91 Volts p-p
            23: 1.80 Volts p-p
            24: 1.71 Volts p-p
            25: 1.62 Volts p-p
            26: 1.53 Volts p-p
            27: 1.44 Volts p-p
            28: 1.37 Volts p-p
            29: 1.29 Volts p-p
            30: 1.22 Volts p-p
            31: 1.16 Volts p-p
            """
        if not 13 <= left <= 31 and not 13 <= right <= 31:
            raise ValueError("Invalid lineout level values.")
        self.write_word(self.CHIP_LINE_OUT_VOL, (right << 8) | left)

    def mic_gain(self, gain):
        """Sets microphone amplifier gain.
        Args:
            gain (int): dB gain"""
        if gain >= 40:
            preamp_gain = 3
            gain -= 40
        elif gain >= 30:
            preamp_gain = 2
            gain -= 30
        elif gain >= 20:
            preamp_gain = 1
            gain -= 20
        else:
            preamp_gain = 0

        input_gain = (gain * 2) // 3
        if input_gain > 15:
            input_gain = 15
        self.write_word(self.CHIP_MIC_CTRL, 0x0170 | preamp_gain)
        self.write_word(self.CHIP_ANA_ADC_CTRL, (input_gain << 4) | input_gain)

    def modify_word(self, cmd, data, mask):
        """Modify double byte to SGTL5000 using mask.
        Args:
            cmd (byte): Command address to write
            data (int): Int to write
            mask (int): Bit mask defines what bits to modify
        """
        old_data = self.read_word(cmd)
        data = (old_data & ~mask) | data
        self.write_word(cmd, data)

    def mute_dac(self, mute=True):
        """Mute or unmute the left and right DAC channels.
        Args:
            mute (bool): True=Mute (default), False=Unmute"""
        if mute:
            self.adc_dac_ctrl |= (3 << 2)
        else:
            self.adc_dac_ctrl &= ~(3 << 2)
        self.write_word(self.CHIP_ADCDAC_CTRL, self.adc_dac_ctrl)

    def mute_headphone(self, mute=True):
        """Mute or unmute the headphone outputs.
        Args:
            mute (bool): True=Mute (default), False=Unmute"""
        if mute:
            self.analog_ctrl |= (1 << 4)
        else:
            self.analog_ctrl &= ~(1 << 4)
        self.write_word(self.CHIP_ANA_CTRL, self.analog_ctrl)

    def mute_lineout(self, mute=True):
        """Mute or unmute the lineout.
        Args:
            mute (bool): True=Mute (default), False=Unmute"""
        if mute:
            self.analog_ctrl |= (1 << 8)
        else:
            self.analog_ctrl &= ~(1 << 8)
        self.write_word(self.CHIP_ANA_CTRL, self.analog_ctrl)

    def peq_filters(self, filters):
        """Set the 7-Band Parametric EQ filter count.
        Args:
            filters (int): Set to Enable the PEQ filters
                           0x0 = Disabled
                           0x1 = 1 Filter Enabled
                           0x2 = 2 Filters Enabled
                           .....
                           0x7 = Cascaded 7 Filters
        Notes:
            select_eq must be set to 1 in order to enable the PEQ"""
        if not 0 <= filters <= 7:
            raise ValueError("Invalid filter count value.")
        self.write_word(self.DAP_PEQ, filters)

    def read_word(self, cmd):
        """Read double byte from SGTL5000.
        Args:
            cmd (byte): Command address to read
        Returns:
            int: value
        """
        buf = self.i2c.readfrom_mem(self.address, cmd, 2, addrsize=16)
        return int.from_bytes(buf, 'big', True)

    def select_eq(self, eq):
        """Selects PEQ, GEQ, Tone Control or disabled
        Args:
            eq (int): 0=Disabled
                      1=Enable PEQ (7-Band Parametric EQ)*
                      2=Enable GEQ (5-Band Graphic EQ)
                      3=Enable Tone Control
        Notes:
            *peq_filters must also be set to the desired number of filters
             in order for the PEQ to be enabled."""
        if not 0 <= eq <= 3:
            raise ValueError("Invalid eq value.")
        self.write_word(self.DAP_AUDIO_EQ, eq)

    def set_eq_band(self, band, level):
        """Sets the specific EQ band.
        Args:
            band(int): 0=Bass
                       1=Mid bass
                       2=Midrange
                       3=Mid treble
                       4=Treble
            level(float): Volume level -.1 to 1 (-100% to 100%)"""
        if not 0 <= band <= 4:
            raise ValueError("Invalid band value.")
        if not -1 <= level <= 1:
            raise ValueError("Invalid level value.")
        # Scale level percent to integer 0 (-11.75 dB) to 95 (12 dB)
        level = (level * 48) + 0.499
        if level < -47:
            level = -47
        if level > 48:
            level = 48
        level += 47
        self.write_word(self.DAP_AUDIO_EQ_BASS_BAND0 + (band * 2), level)

    def set_eq_bands(self, bass=0, mid_bass=0, midrange=0, mid_treble=0,
                     treble=0):
        """Set all EQ bands.
        Args:
            bass(float): Bass level -.1 to 1 (Default=0)
            mid_bass(float): Mid_bass level -.1 to 1 (Default=0)
            midrange(float): Midrange level -.1 to 1 (Default=0)
            mid_treble(float): Mid_treble level -.1 to 1 (Default=0)
            treble(float): Treble level -.1 to 1 (Default=0)"""
        self.set_eq_band(0, bass)
        self.set_eq_band(1, mid_bass)
        self.set_eq_band(2, midrange)
        self.set_eq_band(3, mid_treble)
        self.set_eq_band(4, treble)

    def set_eq_filter(self, filter_index, filter_parameters):
        """Set PEQ coefficient loader.
        Args:
            filter_index(int): Index for the 7 bands of the filter coefficient.
            filter_parameters(List(int)): List of filter coefficients
        """
        # *** Not tested
        self.write_word(self.DAP_FILTER_COEF_ACCESS, filter_index)
        self.write_word(self.DAP_COEF_WR_B0_MSB,
                        (filter_parameters[0] >> 4) & 65535)
        self.write_word(self.DAP_COEF_WR_B0_LSB, filter_parameters[1] & 15)
        self.write_word(self.DAP_COEF_WR_B1_MSB,
                        (filter_parameters[2] >> 4) & 65535)
        self.write_word(self.DAP_COEF_WR_B1_LSB, filter_parameters[3] & 15)
        self.write_word(self.DAP_COEF_WR_B2_MSB,
                        (filter_parameters[4] >> 4) & 65535)
        self.write_word(self.DAP_COEF_WR_B2_LSB, filter_parameters[5] & 15)
        self.write_word(self.DAP_COEF_WR_A1_MSB,
                        (filter_parameters[6] >> 4) & 65535)
        self.write_word(self.DAP_COEF_WR_A1_LSB, filter_parameters[7] & 15)
        self.write_word(self.DAP_COEF_WR_A2_MSB,
                        (filter_parameters[8] >> 4) & 65535)
        self.write_word(self.DAP_COEF_WR_A2_LSB, filter_parameters[9] & 15)
        self.write_word(self.DAP_FILTER_COEF_ACCESS, 0x100 | filter_index)

    def set_surround_sound(self, select, width=4):
        """Set Freescale surround selection.
        Args:
            select (int): 0=Disable
                          1=Disable
                          2=Mono input enable
                          3=Stereo input enable
            width (int): Freescale surround width control. The width control
                         changes the perceived width of the sound field.
                         0=Least width, 7=Most width, 4 Default"""
        if not 0 <= width <= 7:
            raise ValueError("Invalid select value.")
        if not 0 <= select <= 3:
            raise ValueError("Invalid width value.")
        self.write_word(self.DAP_SGTL_SURROUND, (width << 4) | select)

    def volume(self, left, right):
        """Set headphone left and right channel volume.
        Args:
            left (float): left channel volume 0 (mute) to 1 (full)
            right (float): right channel volume 0 (mute) to 1 (full)
        """
        if not 0 <= left <= 1 and not 0 <= right <= 1:
            raise ValueError("Invalid headphone volume values.")

        volume = (((0x7F - self.calc_volume(right)) << 8) |
                  (0x7F - self.calc_volume(left)))
        self.write_word(self.CHIP_ANA_HP_CTRL, volume)

    def write_word(self, cmd, data):
        """Write double byte to SGTL5000.
        Args:
            cmd (byte): Command address to write
            data (int): Int to write
        """
        self.i2c.writeto_mem(self.address,
                             cmd,
                             data.to_bytes(2, 'big'),
                             addrsize=16)
