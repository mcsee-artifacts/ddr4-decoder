# This class is an immutable dictionary whose csvfile_line (0, 1 or x) are printed as strings ('Zero', 'One' or 'DontCare')
from util.py_helper import printf


class InputSignal:
    values = dict()

    def __init__(self, values: dict):
        # e.g.: csvfile_line = { 'CA0': 1, 'CA1': 0 }
        self.values = values

    # @param signal_name should be a key of self.csvfile_line else is dont care, or throws an error if strict.
    # @param strict throws an error if the value is dontcare. Never used yet.
    def get_signal_value(self, signal_name: str, strict: bool = False) -> str:
        value2str = {0: "Zero", 1: "One"}
        if signal_name not in self.values:
            if strict:
                printf(f"could not find signal {signal_name} in map of signal values")
                exit(-1)
            else:
                # if it is not in the map we assume it is a "don't care" bit
                return "DontCare"
        return value2str[self.values[signal_name]]

    # @param input_dx the input identifier, for example 3 for D3.
    # @param strict transmitted to get_signal_value.
    def get_input_value(self, input_dx: int, input2signalname, strict: bool = False):
        input_identifier = f"D{input_dx}"
        if input_identifier not in input2signalname:
            printf(f"could not find input identifier {input_identifier} in input2signalname map")
            exit(-1)
        signal_name = input2signalname[input_identifier]
        return self.get_signal_value(signal_name, strict)
