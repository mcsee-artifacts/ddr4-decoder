import itertools
import re
import time
import typing
import vxi11

from pathlib import PureWindowsPath
from configuration.constants import CmdStr, ValueStr
from configuration.input_signal import InputSignal
from util.py_helper import printf
from util.units import Units

input2signalname = {
    'D0': 'CK0',
    'D1': 'CS',
    'D2': 'CA1',
    'D3': 'CA2',
    'D4': 'CA0',
    'D5': 'unused',
    'D6': 'CA9',
    'D7': 'CA8',
    'D8': 'CA6',
    'D9': 'CA4',
    'D10': 'CA10',
    'D11': 'CA11',
    'D12': 'CA12',
    'D13': 'CA3',
    'D14': 'CA5',
    'D15': 'CA7',
    'D16': 'unused',
    'D17': 'unused'
}

SCOPE_IP = "172.31.200.250"
# DATA_DIR = PureWindowsPath("F:\\", "eth_shared_folder_ramdisk", "data")
# DATA_DIR = PureWindowsPath("D:\\", "comsec-data")
DATA_DIR = PureWindowsPath("R:\\")
SETUP_FILENAME = "setup.lss"


def get_param(param_str: str):
    return fr"vbs? 'return={param_str}'"


def set_param(param_str: str, value: typing.Any = None):
    if value is None:
        return fr"vbs '{param_str}'"
    if type(value) == bool or ("true" in value.lower() or "false" in value.lower()):
        p = f"vbs '{param_str} = {value}'"
    else:
        p = f"vbs '{param_str} = \"{value}\"'"
    return p


def wait(instr: vxi11.Instrument, timeout: int = 60):
    # wait at most 'timeout' seconds until the last operation completed and device becomes idle
    instr.ask(get_param(f"{CmdStr.WAIT_UNTIL_IDLE}({timeout})"))


def save_setup_file(dir_suffix: str, instr: vxi11.Instrument):
    printf(f"saving setup file (setup.lss) to disk")
    instr.write(set_param(ValueStr.SAVE_WAVEFORM_SAVETO, "File"))
    instr.write(set_param(ValueStr.SAVE_WAVEFORM_EN_COUNTER_SUFFIX, False))
    target_dir = PureWindowsPath(DATA_DIR, f"{dir_suffix}")
    instr.write(set_param(ValueStr.SAVE_SETUP_FILENAME, str(PureWindowsPath(target_dir, SETUP_FILENAME))))
    instr.write(set_param(CmdStr.SAVE_SETUP))


def load_setup_file(setup_filepath: str,  instr: vxi11.Instrument):
    if not setup_filepath.endswith(".lss"):
        printf(f"given setup file {setup_filepath} must be of type .lss to be loadable.")
        exit(-1)
    printf(f"loading setup file at {setup_filepath} from disk")
    instr.write(set_param("app.SaveRecall.Setup.RecallSetupFilename", setup_filepath))
    instr.write(set_param("app.SaveRecall.Setup.RecallFrom", "File"))
    instr.write(set_param("app.SaveRecall.Setup.DoRecallSetupFileDoc2"))
    wait(instr)


def configure_ch(instr: vxi11.Instrument, channel_no: int, ver_scale_variable: bool, ver_scale: str,
                 ver_offset: str, alias: str, target_grid: str, deskew_value: str):
    # enable channel
    instr.write(set_param(ValueStr.for_channel(channel_no, ValueStr.p_ACQ_CHX_VIEW), True))
    instr.write(set_param(ValueStr.for_channel(channel_no, ValueStr.p_ACQ_CHX_INPUT), "InputA"))  # upper

    # set vertical scale
    instr.write(set_param(ValueStr.for_channel(channel_no, ValueStr.p_ACQ_CHX_VER_VARIABLE), ver_scale_variable))
    instr.write(set_param(ValueStr.for_channel(channel_no, ValueStr.p_ACQ_CHX_VER_SCALE), ver_scale))

    # set input offset
    instr.write(set_param(ValueStr.for_channel(channel_no, ValueStr.p_ACQ_CHX_VER_OFFSET), ver_offset))

    # set deskew
    instr.write(set_param(ValueStr.for_channel(channel_no, ValueStr.p_ACQ_CHX_DESKEW), deskew_value))

    # set label
    instr.write(set_param(ValueStr.for_channel(channel_no, ValueStr.p_ACQ_CHX_ALIAS), alias))

    # place on grid
    instr.write(set_param(ValueStr.for_channel(channel_no, ValueStr.p_ACQ_CHX_GRID), target_grid))


def disable_ch(instr: vxi11.Instrument, channel_no: int):
    printf(f"disabling channel C{channel_no}")
    instr.write(set_param(ValueStr.for_channel(channel_no, ValueStr.p_ACQ_CHX_VIEW), False))


def save_memory(instr: vxi11.Instrument, memory_no: int, out_format: str, out_dir: str, file_format: str = "WaveML"):
    instr.write(set_param(ValueStr.SAVE_WAVEFORM_SRC, f"M{memory_no}"))
    instr.write(set_param(ValueStr.SAVE_WAVEFORM_SAVETO, "File"))
    if out_format not in ["Lines", "BusValue"]:
        printf(f"unrecognized output format {out_format}")
        exit(-1)
    instr.write(set_param(ValueStr.SAVE_WAVEFORM_SUBFORMAT, out_format))
    wait(instr)

    # WaveML produces the binary XMLdig file
    if file_format not in ["Excel", "WaveML"]:
        printf(f"unrecognized file format {file_format}")
        exit(-1)

    instr.write(set_param(ValueStr.SAVE_WAVEFORM_WVFORMAT, file_format))
    instr.write(set_param(ValueStr.SAVE_WAVEFORM_TITLE, "trace"))
    instr.write(set_param(ValueStr.SAVE_WAVEFORM_EN_COUNTER_SUFFIX, True))
    instr.write(set_param(ValueStr.SAVE_WAVEFORM_EN_SRC_SUFFIX, True))
    instr.write(set_param(ValueStr.SAVE_WAVEFORM_DIR, out_dir))
    wait(instr)

    instr.write(set_param(CmdStr.SAVE_WAVEFORM))
    wait_opc(instr)


def load_or_return_default(key: str, config: dict, default_value: any):
    return config[key] if (key in config) else default_value


def wait_opc(instr: vxi11.Instrument):
    while True:
        try:
            if int(instr.ask("*OPC?")) == 1:
                return
        except vxi11.vxi11.Vxi11Exception:
            time.sleep(2)


def connect() -> vxi11.Instrument:
    instr = vxi11.Instrument(SCOPE_IP)
    instr.timeout = 60
    # disable returning header with response
    instr.write("COMM_HEADER OFF")
    wait_opc(instr)
    # print device information
    # printf(f"connected to {instr.ask('*IDN?').replace(',', ' ')}")
    return instr


def setup_ddr_option(instr: vxi11.Instrument, output_dir_suffix: str, cfg: dict):
    # enable 'auto' triggering mode
    new_trigger_mode = 'normal'
    printf(f"setting trigger mode to {new_trigger_mode}")
    instr.write(set_param(ValueStr.ACQ_TRIGGER_MODE, new_trigger_mode))
    wait(instr)

    DDR_STANDARD = "DDR5"
    DDR_SPEED = cfg['speedgrade']
    # TODO extract these from the 'cfg' dictionary once it is clear which unit it is supposed to be
    READ_LATENCY = cfg['timing'][0]  # CL
    WRITE_LATENCY = cfg['timing'][0]  # CL

    # DDR Debug Toolkit setup
    printf(f"configuring DDR Debug:")
    print(f"    assuming {DDR_STANDARD}-{DDR_SPEED} with latencies R={READ_LATENCY}, W={WRITE_LATENCY}")
    configure_ddr_debug_toolkit(DDR_SPEED, DDR_STANDARD, READ_LATENCY, WRITE_LATENCY, instr)

    # decoder setup
    configure_serial_decoder(DDR_SPEED, DDR_STANDARD, READ_LATENCY, WRITE_LATENCY, output_dir_suffix, instr)

    # reapply signal names as DDR debug + decoder changed them
    setup_digital1_bus(instr)


def configure_ddr_debug_toolkit(DDR_SPEED, DDR_STANDARD, READ_LATENCY, WRITE_LATENCY, instr):
    # ================================================================
    # tab: DDR debug =================================================
    # ================================================================

    instr.write(set_param(ValueStr.DDR_DBG_EnableDDRA, True))
    # configure protocol and speed grade
    instr.write(set_param(ValueStr.DDR_DBG_Protocol, DDR_STANDARD))
    instr.write(set_param(ValueStr.DDR_DBG_SpeedGrade, DDR_SPEED))
    # enable View1 and configure DQ (C1), DQS (C2); set analysis type: bus
    instr.write(set_param(ValueStr.DDR_DBG_EnableView, True))
    instr.write(set_param(ValueStr.DDR_DBG_EnableDQ, True))
    instr.write(set_param(ValueStr.DDR_DBG_DataSource, "C1"))
    instr.write(set_param(ValueStr.DDR_DBG_EnableDQS, True))
    instr.write(set_param(ValueStr.DDR_DBG_StrobeSource, "C2"))
    instr.write(set_param(ValueStr.DDR_DBG_EnableCK, False))
    instr.write(set_param(ValueStr.DDR_DBG_TableRows, "4"))
    instr.write(set_param(ValueStr.DDR_DBG_Analysis, "BUS"))

    # ================================================================
    # tab: CMD bus & decoder =========================================
    # ================================================================

    # configure command bus: signal inputs
    instr.write(set_param(ValueStr.DDR_DBG_MSOSourceWE, "D0"))  # CA0
    instr.write(set_param(ValueStr.DDR_DBG_EnableWE, True))
    instr.write(set_param(ValueStr.DDR_DBG_MSOSourceCS, "D1"))  # CS_n
    instr.write(set_param(ValueStr.DDR_DBG_EnableCS, True))
    instr.write(set_param(ValueStr.DDR_DBG_MSOSourceCAS, "D2"))  # CA2
    instr.write(set_param(ValueStr.DDR_DBG_EnableCAS, True))
    instr.write(set_param(ValueStr.DDR_DBG_MSOSourceCA4, "D3"))  # CA4
    instr.write(set_param(ValueStr.DDR_DBG_EnableCA4, True))
    instr.write(set_param(ValueStr.DDR_DBG_MSOSourceACT, "D6"))  # CA3
    instr.write(set_param(ValueStr.DDR_DBG_EnableACT, True))
    instr.write(set_param(ValueStr.DDR_DBG_MSOSourceRAS, "D7"))  # CA1
    instr.write(set_param(ValueStr.DDR_DBG_EnableRAS, True))
    instr.write(set_param(ValueStr.DDR_DBG_MSOSourceCA5, "D17"))  # CA5 is not in the GUI
    instr.write(set_param(ValueStr.DDR_DBG_EnableCA5, False))
    instr.write(set_param(ValueStr.DDR_DBG_MSOSourceCLK, "D10"))  # CLK
    instr.write(set_param(ValueStr.DDR_DBG_EnableCLK, True))
    instr.write(set_param(ValueStr.DDR_DBG_MSOSourceCA6, "D12"))  # CA10
    instr.write(set_param(ValueStr.DDR_DBG_EnableCA6, True))
    instr.write(set_param(ValueStr.DDR_DBG_MSOSourceCA12, "D13"))  # CA12
    instr.write(set_param(ValueStr.DDR_DBG_EnableCA12, True))
    instr.write(set_param(ValueStr.DDR_DBG_MSOSourceCKE, "D8"))  # CA9
    instr.write(set_param(ValueStr.DDR_DBG_EnableCKE, True))

    # enable r/w separation
    # instr.write(set_param(ValueStr.DDR_DBG_EnableRWSepUsingCmdBus, True))

    # set read/write latency
    # instr.write(set_param(ValueStr.DDR_DBG_CmdBusShow, True))
    instr.write(set_param(ValueStr.DDR_DBG_ReadLatency, READ_LATENCY))
    instr.write(set_param(ValueStr.DDR_DBG_WriteLatency, WRITE_LATENCY))

    # show CMD bus as expanded
    # instr.write(set_param(ValueStr.DDR_DBG_CmdBusShowAs, "Expanded"))

    # enable bus trigger (READ or WRITE)
    # instr.write(set_param(ValueStr.DDR_DBG_CmdBusTrigger, True))
    # instr.write(set_param(ValueStr.DDR_DBG_CmdBusTriggerOn, "ReadorWrite"))

    wait_opc(instr)


def configure_serial_decoder(DDR_SPEED, DDR_STANDARD, READ_LATENCY, WRITE_LATENCY, out_dir, instr):
    printf(f"configuring DDR decoder")
    # view decode
    instr.write(set_param(ValueStr.DECODER_ViewDecode, True))
    # src1 (wfm1)
    instr.write(set_param(ValueStr.DECODER_Src1, "C1"))
    # src2 (bus)
    instr.write(set_param(ValueStr.DECODER_Src2, "Digital1"))
    # src3 (wfm2)
    instr.write(set_param(ValueStr.DECODER_Src3, "C2"))
    # protocol: DDR Cmd Bus
    instr.write(set_param(ValueStr.DECODER_Protocol, "DDRCmdBus"))
    # DDR standard
    instr.write(set_param(ValueStr.DECODER_DDRProtocol, DDR_STANDARD))
    instr.write(set_param(ValueStr.DECODER_SpeedGrade, DDR_SPEED))

    # signals: DDR CMD Bus Decode
    instr.write(set_param(ValueStr.DECODER_Dnum_ACT, "D13"))
    instr.write(set_param(ValueStr.DECODER_Dnum_CA4, "D7"))
    instr.write(set_param(ValueStr.DECODER_Dnum_CAS, "D3"))
    instr.write(set_param(ValueStr.DECODER_Dnum_CKE, "NC"))  # not configured as CKE is not available
    instr.write(set_param(ValueStr.DECODER_Dnum_CS, "D1"))
    instr.write(set_param(ValueStr.DECODER_Dnum_RAS, "D2"))
    instr.write(set_param(ValueStr.DECODER_Dnum_WE, "D4"))
    # latencies
    instr.write(set_param(ValueStr.DECODER_ReadLatency, READ_LATENCY))
    instr.write(set_param(ValueStr.DECODER_WriteLatency, WRITE_LATENCY))

    # signals: DDR5 & LPDDR5
    instr.write(set_param(ValueStr.DECODER_Dnum_CA5_9, "D8"))
    instr.write(set_param(ValueStr.DECODER_Dnum_CA6_10, "D9"))
    instr.write(set_param(ValueStr.DECODER_Dnum_CA12, "D10"))

    # set path to save decoder table
    instr.write(set_param("app.SaveRecall.Table.TableDir",
                          str(PureWindowsPath(DATA_DIR, out_dir))))
    instr.write(set_param("app.SaveRecall.Table.SaveSource", "Decode1"))
    instr.write(set_param("app.SaveRecall.EnableTableOnAutoSave", True))
    instr.write(set_param("app.SaveRecall.Table.EnableSourcePrefix", False))
    wait_opc(instr)
    instr.write(set_param("app.SaveRecall.Table.SaveFile"))
    wait_opc(instr)


def reset_device(instr: vxi11.Instrument):
    # set device to default csvfile_line
    printf(f"resetting device to default setup")
    instr.write(set_param(CmdStr.DEFAULT_SETUP))
    wait_opc(instr)


def setup(instr: vxi11.Instrument, config: dict, dir_suffix: str, enable_analog_chs: bool = False):
    u = Units()

    # hide the clock to get more screen space
    instr.write(set_param(ValueStr.HIDE_CLOCK, True))

    # set device to default csvfile_line
    reset_device(instr) 

    # enable 'auto' triggering mode
    new_trigger_mode = 'stopped'
    printf(f"setting trigger mode to {new_trigger_mode}")
    instr.write(set_param(ValueStr.ACQ_TRIGGER_MODE, new_trigger_mode))
    wait(instr)

    # CHANNEL C1/C2 ####################################################
    if enable_analog_chs:
        instr.write(set_param(ValueStr.DISPLAY_GRIDMODE, "Dual"))
        # configure_ch(instr, 1, False, "0.200", "-1.1", "DQ0_A", "YT2", "-0.0000001057926")
        configure_ch(instr, 1, False, "0.200", "-1.1", "DQ0_A", "YT2", "0.00000000005940")
        # configure_ch(instr,2, True, "0.235", "0", "DQS0_A", "YT2", "-0.000000005928")
        configure_ch(instr, 2, True, "0.235", "0", "DQS0_A", "YT2", "0.000000000243")
    else:
        instr.write(set_param(ValueStr.DISPLAY_GRIDMODE, "Single"))
        disable_ch(instr, 1)
        disable_ch(instr, 2)

    # DIGITAL1 BUS ######################################################

    printf(f"enabling 'Digital1' bus")
    setup_digital1_bus(instr)

    # LOGIC SETUP #######################################################

    # lines that need special thresholds
    thresholds = {
        'CK0': "0",  # because CK0 is differential
    }

    # lines that are inverted
    inverted_lines = ['CK0']
    # set thresholds
    for idx, (k, v) in enumerate(input2signalname.items()):
        thresh1 = thresholds[v] if (v in thresholds) else "0.795"  # volts
        thresh2 = f"-{thresh1}" if (v in inverted_lines) else thresh1
        instr.write(set_param(f"{ValueStr.LA_THRESHOLD}{idx}", thresh2))
        if v in inverted_lines:
            p_str = ValueStr.for_channel(idx, ValueStr.p_LA_INVERT)
            instr.write(set_param(p_str, True))

    wait(instr)

    # TIMEBASE SETTINGS #################################################

    # set timebase mode
    value = load_or_return_default(ValueStr.ACQ_HOR_SCALE, config, u.ns_to_sec(5))
    instr.write(set_param(ValueStr.ACQ_HOR_SCALE, value))

    # set sampling rate
    # instr.write(set_param(ValueStr.ACQ_HOR_SAMPLE_PTS, "FixedSampleRate"))
    # value = load_or_return_default(ValueStr.ACQ_HOR_SAMPLE_RATE, config, f"{20_000_000_000}")
    instr.write(set_param(ValueStr.ACQ_HOR_SAMPLE_PTS, "SetMaximumMemory"))
    instr.write(set_param(ValueStr.ACQ_HOR_SAMPLE_MAX_SMPL, str(20_000_000)))
    instr.write(set_param(ValueStr.ACQ_HOR_SAMPLE_RATE, value))

    # horizontal position of the trigger (pre-/post-trigger acq. time)
    value = load_or_return_default(ValueStr.ACQ_HOR_OFFSET, config, u.ns_to_sec(-20))
    instr.write(set_param(ValueStr.ACQ_HOR_OFFSET, value))

    # TRIGGER: AUX via USB ############################
    setup_aux_trigger(instr)

    # CONFIGURE TARGET DIRECTORY ########################################

    # ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    # target_dir = PureWindowsPath(DATA_DIR, f"{ts}_{dir_suffix}")
    target_dir = PureWindowsPath(DATA_DIR, f"{dir_suffix}")

    # PREPARE ACQUISITION USING AUTO-SAVE ###############################

    configure_autosave(instr, str(target_dir))


def configure_autosave(instr: vxi11.Instrument, target_dir: str):
    # open the auto-save tab
    instr.write(set_param(CmdStr.SAVE_SHOW_AUTOSAVE))

    trigger_mode = "auto"
    printf(f"setting trigger mode to {trigger_mode.upper()} and activating autosave for waveform and table")
    instr.write(set_param(ValueStr.ACQ_TRIGGER_MODE, trigger_mode))
    wait_opc(instr)

    # WAVEFORM
    instr.write(set_param(ValueStr.SAVE_WAVEFORM_ENABLE_AUTOSAVE, True))
    instr.write(set_param(ValueStr.SAVE_WAVEFORM_SRC, "Digital1"))
    instr.write(set_param(ValueStr.SAVE_WAVEFORM_TITLE, "trace"))
    instr.write(set_param(ValueStr.SAVE_WAVEFORM_EN_COUNTER_SUFFIX, True))
    instr.write(set_param(ValueStr.SAVE_WAVEFORM_EN_SRC_SUFFIX, False))
    instr.write(set_param(ValueStr.SAVE_WAVEFORM_DIR, target_dir))
    instr.write(set_param(ValueStr.SAVE_WAVEFORM_WVFORMAT, "WaveML"))

    # FIXME: this does not work somehow. It has been reported to TELEDYNE (09/28/2022)
    # TABLE
    # instr.write(set_param("app.SaveRecall.EnableTableOnAutoSave", True))
    # instr.write(set_param("app.SaveRecall.Table.SaveSource", "Decode1"))
    # instr.write(set_param("app.SaveRecall.Table.TableTitle", "table"))
    # instr.write(set_param("app.SaveRecall.Table.EnableCounterSuffix", True))
    # instr.write(set_param("app.SaveRecall.Table.EnableSourcePrefix", False))
    # instr.write(set_param("app.SaveRecall.Table.TableDir", target_dir))
    # instr.write(set_param("app.SaveRecall.Table.TableFormat", "Excel"))

    instr.write(set_param(CmdStr.SAVE_WAVEFORM))
    wait_opc(instr)
    # instr.write(set_param("app.SaveRecall.Table.SaveFile"))
    # wait(instr)
    # wait_opc(instr)


def setup_digital1_bus(instr):
    instr.write(set_param(ValueStr.LA_VIEW, True))
    instr.write(set_param(ValueStr.LA_GRID, "YT1"))
    instr.write(set_param(ValueStr.LA_DISPLAY_MODE, "LINES"))
    instr.write(set_param(ValueStr.LA_LABEL_MODE, "CUSTOM"))
    # set labels and enable inputs
    # note: this is already included in the DDR5 setup file but we repeat it here so that we have a textual description
    # of the mapping: logical input (Dx) -> signal
    printf(f"adding labels to digital inputs")
    for idx in range(0, len(input2signalname)):
        signal_name = input2signalname[f"D{idx}"]
        instr.write(set_param(f"{ValueStr.LA_SIGNAL_INPUT_NAME}{idx}", signal_name))
        enable_signal = "true" if ("broken" not in signal_name and "unused" not in signal_name) else "false"
        # enable/disable signal input
        instr.write(set_param(f"{ValueStr.LA_SIGNAL_INPUT_ENABLE}{idx}", enable_signal))
        enable_signal = "true" if ("broken" not in signal_name and "unused" not in signal_name) else "false"
        # enable/disable signal input
        instr.write(set_param(f"{ValueStr.LA_SIGNAL_INPUT_ENABLE}{idx}", enable_signal))
    wait(instr)


def setup_aux_trigger(instr):
    # set trigger type
    new_trigger_type = "edge"
    printf(f"configuring trigger type to {new_trigger_type.upper()}")
    instr.write(set_param(ValueStr.ACQ_TRIGGER_TYPE, new_trigger_type))
    # set trigger source to AUX IN
    instr.write(set_param(ValueStr.ACQ_TRIGGER_EDGE_SOURCE, "Ext"))
    # set level threshold to 1.0V
    instr.write(set_param(ValueStr.ACQ_TRIGGER_EDGE_LEVEL, "1.0"))

    # instr.write(set_param("app.Acquisition.Trigger.ExtSlope", "Either"))
    # instr.write(set_param("app.Acquisition.Trigger.ExtSlope", "Positive"))
    instr.write(set_param("app.Acquisition.Trigger.ExtSlope", "Negative"))
    wait(instr)


def setup_pattern_trigger(dram_cmds, instr, trigger_cmd: tuple):
    # set trigger type
    new_trigger_type = "pattern"
    printf(f"configuring trigger type to {new_trigger_type.upper()}, cmd: {trigger_cmd[0]}")
    instr.write(set_param(ValueStr.ACQ_TRIGGER_TYPE, new_trigger_type))
    # only whitelisted signals: clock, signals of trigger pattern (ACT or REF), bank bits, bankgroup bits
    acquisition_whitelist = ['CK0'] \
                            + ['CA6', 'CA7'] \
                            + ['CA8', 'CA9', 'CA10'] \
                            + list(dram_cmds['ACT1'].keys()) \
                            + list(dram_cmds['ACT2'].keys()) \
                            + list(dram_cmds['REF_ANY'].keys())
    # apply trigger pattern
    ips = InputSignal(trigger_cmd[1])
    for idx in range(0, len(input2signalname)):
        val = ips.get_input_value(idx, input2signalname)
        # set bit value of trigger
        instr.write(set_param(f"{ValueStr.ACQ_TRIGGER_DIGITAL_BIT}{idx}", val))
        # configure which signals should be shown on the scope (and included in the trace)
        signal_name = input2signalname[f"D{idx}"]
        show_signal = (signal_name in acquisition_whitelist)
        instr.write(set_param(f"{ValueStr.LA_SIGNAL_INPUT_ENABLE}{idx}", show_signal))
        wait_opc(instr)
    # disable filter (this filter ignores short glitches that last less than 3.5ns)
    instr.write(set_param(ValueStr.ACQ_FILTER_GLITCHES, False))


def start_capture(trigger_mode: str,  min_acquisitions: int = None):
    instr = connect()

    # put performance priority on analysis (instead of display)
    instr.write(set_param(ValueStr.PREF_PERFORMANCE, "Analysis"))
    wait_opc(instr)

    # enable autosave
    instr.write(set_param(ValueStr.SAVE_WAVEFORM_AUTOSAVE, "Wrap"))
    wait_opc(instr)

    printf(f"setting trigger mode to {trigger_mode.upper()}")
    instr.write(set_param(ValueStr.ACQ_TRIGGER_MODE, trigger_mode))
    wait_opc(instr)

    if min_acquisitions is None:
        return

    while True:
        time.sleep(5)
        last_fn = instr.ask(get_param(ValueStr.SAVE_WAVEFORM_LAST_FILEPATH))
        count = int(re.search("(\\d+).csv", PureWindowsPath(last_fn).name).group(1))
        if count >= min_acquisitions:
            instr.write(set_param(ValueStr.SAVE_WAVEFORM_AUTOSAVE, "Off"))
            printf(f"stopping acquisition after {count} captured triggers")
            instr.write(set_param(ValueStr.ACQ_TRIGGER_MODE, "stop"))
            wait(instr)
            break


def stop_capture():
    instr = connect()
    instr.write(set_param(ValueStr.ACQ_TRIGGER_MODE, "stop"))
    wait_opc(instr)

    instr.write(set_param(ValueStr.SAVE_WAVEFORM_AUTOSAVE, "Off"))
    wait_opc(instr)

    instr.write(set_param(ValueStr.PREF_PERFORMANCE, "Display"))
    wait_opc(instr)


def get_scope_configuration(config_no: int):
    sampling_rates = [
        # 2.5 GS/s, 3.13 GS/s, 6.5 GS/s, 12.5 GS/s
        {ValueStr.ACQ_HOR_SAMPLE_RATE: f"{x}"} for x in [
            # 2_500_000_000,
            # 5_000_000_000,
            # 10_000_000_000,
            20_000_000_000
        ]]

    u = Units()
    # hor_offset_scale = [
    #     # { ValueStr.ACQ_HOR_OFFSET: u.ns_to_sec(-2), ValueStr.ACQ_HOR_SCALE: u.ps_to_sec(500) },
    #     # { ValueStr.ACQ_HOR_OFFSET: u.ns_to_sec(-4), ValueStr.ACQ_HOR_SCALE: u.ns_to_sec(1) },
    #     # { ValueStr.ACQ_HOR_OFFSET: u.ns_to_sec(-8), ValueStr.ACQ_HOR_SCALE: u.ns_to_sec(2) },
    #     # { ValueStr.ACQ_HOR_OFFSET: u.ns_to_sec(-20), ValueStr.ACQ_HOR_SCALE: u.ns_to_sec(5) },
    #     # { ValueStr.ACQ_HOR_OFFSET: u.ns_to_sec(-40), ValueStr.ACQ_HOR_SCALE: u.ns_to_sec(10) },
    #     # { ValueStr.ACQ_HOR_OFFSET: u.ns_to_sec(-80), ValueStr.ACQ_HOR_SCALE: u.ns_to_sec(20) },
    #     # { ValueStr.ACQ_HOR_OFFSET: u.ns_to_sec(-200), ValueStr.ACQ_HOR_SCALE: u.ns_to_sec(50) },
    #     # { ValueStr.ACQ_HOR_OFFSET: u.ns_to_sec(-400), ValueStr.ACQ_HOR_SCALE: u.ns_to_sec(100) },
    #     # { ValueStr.ACQ_HOR_OFFSET: u.ns_to_sec(-800), ValueStr.ACQ_HOR_SCALE: u.ns_to_sec(200) },
    #     # { ValueStr.ACQ_HOR_OFFSET: u.us_to_sec(-2), ValueStr.ACQ_HOR_SCALE: u.ns_to_sec(500) },
    #     # { ValueStr.ACQ_HOR_OFFSET: u.us_to_sec(-4), ValueStr.ACQ_HOR_SCALE: u.us_to_sec(1) },
    #     # { ValueStr.ACQ_HOR_OFFSET: u.us_to_sec(-8), ValueStr.ACQ_HOR_SCALE: u.us_to_sec(2) },
    #     # { ValueStr.ACQ_HOR_OFFSET: u.us_to_sec(-20), ValueStr.ACQ_HOR_SCALE: u.us_to_sec(5) },
    #     # { ValueStr.ACQ_HOR_OFFSET: u.us_to_sec(-40), ValueStr.ACQ_HOR_SCALE: u.us_to_sec(10) },
    #     # { ValueStr.ACQ_HOR_OFFSET: u.us_to_sec(-200), ValueStr.ACQ_HOR_SCALE: u.us_to_sec(50) },
    #     # { ValueStr.ACQ_HOR_OFFSET: u.us_to_sec(-400), ValueStr.ACQ_HOR_SCALE: u.us_to_sec(100) },
    #     # { ValueStr.ACQ_HOR_OFFSET: u.us_to_sec(-800), ValueStr.ACQ_HOR_SCALE: u.us_to_sec(200) },
    #     # { ValueStr.ACQ_HOR_OFFSET: u.us_to_sec(-800), ValueStr.ACQ_HOR_SCALE: u.us_to_sec(500) },
    #     # { ValueStr.ACQ_HOR_OFFSET: u.ms_to_sec(-2), ValueStr.ACQ_HOR_SCALE: u.us_to_sec(500) },
    #     { ValueStr.ACQ_HOR_OFFSET: u.ms_to_sec(-4), ValueStr.ACQ_HOR_SCALE: u.ms_to_sec(1) },  # THIS WORKS!
    #     # { ValueStr.ACQ_HOR_OFFSET: u.ms_to_sec(-8), ValueStr.ACQ_HOR_SCALE: u.ms_to_sec(2) },
    #     # { ValueStr.ACQ_HOR_OFFSET: u.ms_to_sec(-20), ValueStr.ACQ_HOR_SCALE: u.ms_to_sec(5) },
    #     # { ValueStr.ACQ_HOR_OFFSET: u.ms_to_sec(-40), ValueStr.ACQ_HOR_SCALE: u.ms_to_sec(10) },
    #     # { ValueStr.ACQ_HOR_OFFSET: u.ms_to_sec(-80), ValueStr.ACQ_HOR_SCALE: u.ms_to_sec(20) },
    # ]

    hor_offset_scale = [
        # { ValueStr.ACQ_HOR_SCALE: u.ps_to_sec(500) },
        # { ValueStr.ACQ_HOR_SCALE: u.ns_to_sec(1) },
        # { ValueStr.ACQ_HOR_SCALE: u.ns_to_sec(2) },
        # { ValueStr.ACQ_HOR_SCALE: u.ns_to_sec(5) },
        # { ValueStr.ACQ_HOR_SCALE: u.ns_to_sec(10) },
        # { ValueStr.ACQ_HOR_SCALE: u.ns_to_sec(20) },
        # { ValueStr.ACQ_HOR_SCALE: u.ns_to_sec(50) },
        # { ValueStr.ACQ_HOR_SCALE: u.ns_to_sec(100) },
        # { ValueStr.ACQ_HOR_SCALE: u.ns_to_sec(200) },
        # { ValueStr.ACQ_HOR_SCALE: u.ns_to_sec(500) },
        # { ValueStr.ACQ_HOR_SCALE: u.us_to_sec(1) },
        # { ValueStr.ACQ_HOR_SCALE: u.us_to_sec(2) },
        # { ValueStr.ACQ_HOR_SCALE: u.us_to_sec(5) },
        # { ValueStr.ACQ_HOR_SCALE: u.us_to_sec(10) },
        { ValueStr.ACQ_HOR_SCALE: u.us_to_sec(20) },
        # { ValueStr.ACQ_HOR_SCALE: u.us_to_sec(50) },
        # { ValueStr.ACQ_HOR_SCALE: u.us_to_sec(100) },  # WORKS
        # { ValueStr.ACQ_HOR_SCALE: u.us_to_sec(200) },
        # { ValueStr.ACQ_HOR_SCALE: u.us_to_sec(500) },
        # { ValueStr.ACQ_HOR_SCALE: u.ms_to_sec(1) },
        # { ValueStr.ACQ_HOR_SCALE: u.ms_to_sec(2) },
        # { ValueStr.ACQ_HOR_SCALE: u.ms_to_sec(5) },
        # { ValueStr.ACQ_HOR_SCALE: u.ms_to_sec(10) },
        # { ValueStr.ACQ_HOR_SCALE: u.ms_to_sec(20) },
    ]

    for e in hor_offset_scale:
        # empirically determined that this delay works well with our AUX trigger to capture at much as possible
        # e[ValueStr.ACQ_HOR_OFFSET] = str(round(-(float(e[ValueStr.ACQ_HOR_SCALE])*10/2*1.79), 12))
        e[ValueStr.ACQ_HOR_OFFSET] = str(round(-(float(e[ValueStr.ACQ_HOR_SCALE])*16), 12))
        # e[ValueStr.ACQ_HOR_OFFSET] = "-0.00050"

    all_configs = list()
    for _, subset in enumerate(itertools.product(sampling_rates, hor_offset_scale)):
        all_configs.append({k: v for d in subset for k, v in d.items()})

    if config_no >= len(all_configs):
        printf(f"given configuration no. ({config_no}) is invalid!")
        exit(-1)
    printf(f"loading configuration #{config_no}")
    return all_configs[config_no]
