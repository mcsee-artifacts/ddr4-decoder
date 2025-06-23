import os
import re

from collections import defaultdict

from ..py_helper import printf
from .enums import E_DRAM_CMD, E_DRAM_TYPE

# HACK: This is populated in __init__.py to avoid a circular import.
DRAM_COMMANDS = {}


class DramCommand:
    def __init__(self, type: E_DRAM_TYPE, name: E_DRAM_CMD, signal_reqs: dict, sub_cmds: list["DramCommand"] = []):
        self.type = type
        self.is_two_cycle_cmd = (len(sub_cmds) > 0)
        self.identifier = name
        self.metadata = dict()
        self.extracted_signals = False
        self.requirements = signal_reqs
        self.cmds = sub_cmds  # This and get_commands are a bit confusing

    def __eq__(self, other):
        if isinstance(other, DramCommand):
            return str(self.identifier) == str(other.identifier)
        elif isinstance(other, E_DRAM_CMD):
            return self.identifier == other
        return False

    @classmethod
    def as_two_cycle_cmd(cls, name: E_DRAM_CMD, sub_cmds: list):
        assert all([type(x) == DramCommand for x in sub_cmds]), "as_two_cycle_cmd expects a list of DramCommand"
        # the JEDEC standard says that CA1 is used to distinguish between a 1-cycle and a 2-cycle command,
        # => make sure that CA1 is ALWAYS 0 in the first of sub_cmds (i.e., first cycle)
        assert sub_cmds[0].requirements['CA1'] == 0, "first clock of 2-cycle cmd does not satisfy CA1==0"
        # Two cycle commands only exist for DDR5 (as of now).
        return cls(E_DRAM_TYPE.ddr5, name, {}, sub_cmds)

    # use a forward declaration to avoid DramCommand complaining, see https://stackoverflow.com/a/44798831/3017719
    def add_subcommand(self, cmd: "DramCommand"):
        self.cmds.append(cmd)
        self.extracted_signals = all([v.extracted_signals for v in self.get_commands()])

    def match_name(self, signal_name: str):
        return signal_name == str(self.identifier)

    # Returns a list of regexes that correspond to each of the subsequent commands, usable directly on the CSV
    # file rows as strings
    def get_regexes(self, column_names: list, dram_cmds: list["DramCommand"], compiled: bool = False) -> list:
        ret = []
        for command in dram_cmds:
            cmd_regex = r"^"
            for column_name_id, column_name in enumerate(column_names):
                if column_name_id:
                    cmd_regex += ','
                if column_name in command.requirements:
                    if command.requirements[column_name] not in [0, 1]:
                        raise Exception(
                            f"I do not understand requirement `{command.requirements[column_name]}`for DRAM command `{self.identifier}`")
                    cmd_regex += str(command.requirements[column_name])
                else:
                    cmd_regex += r"[^,]*"

            ret.append(cmd_regex)

        if compiled:
            import re
            return list(map(re.compile, ret))
        else:
            return ret

    def __str__(self):
        return str(self.identifier).replace('E_DRAM_CMD.', '')

    def __lt__(self, other):
        return self.identifier < other.identifier

    def add_metadata(self, name: str, format_str: str, description: str = None, abbreviation: str = None):
        self.metadata[name] = {
            'description': description,
            'value': None,
            'abbreviation': abbreviation,
            'format_str': format_str
        }
        return self

    def has_metadata(self):
        return any([len(v.metadata) > 0 for v in self.get_commands()])

    def get_commands(self, first_cycle: bool = True, second_cycle: bool = True) -> list["DramCommand"]:
        if self.is_two_cycle_cmd:
            if first_cycle and second_cycle:
                return self.cmds
            elif first_cycle:
                return [self.cmds[0]]
            elif second_cycle:
                return [self.cmds[1]]
            else:
                raise Exception("get_command must be called with first_cycle=True and/or second_cyle=True")
        else:
            return [self]

    @staticmethod
    def get_command(gen: E_DRAM_TYPE, cmd_identifier: E_DRAM_CMD):
        for cmd in DRAM_COMMANDS[gen]:
            # this is important here as cmd_identifier might be without the enum suffix "E_DRAM_CMD."
            if str(cmd_identifier) in str(cmd.identifier):
                return cmd
        return None

    @staticmethod
    def check_signals_extracted(all_cmds: list["DramCommand"]):
        if not all([k.extracted_signals for k in all_cmds]):
            printf(f"get_metadata_str requires prior call to match_signals to extract metadata")
            exit(os.EX_USAGE)

    def get_metadata_str(self) -> str:
        all_cmds = self.get_commands()
        self.check_signals_extracted(all_cmds)

        signal_data = self.get_metadata()
        out_str = ""
        for k, v in signal_data.items():
            out_str += f"{k}: {v}, "
        return out_str

    def get_metadata(self) -> dict[str]:
        all_cmds = self.get_commands()
        self.check_signals_extracted(all_cmds)

        out_data = defaultdict(str)
        for cmd in all_cmds:
            # get all abbreviations
            all_abbrvs = set([v['abbreviation'] for k,v in cmd.metadata.items()])

            # for each abbreviation, get all collected metadata entries to build a map: bit no -> value
            for abbrv in all_abbrvs:
                bitpos_value = dict()
                for _, data in cmd.metadata.items():
                    if abbrv in data['abbreviation']:
                        bit_pos = int(str(re.findall(r'\d+', data['description'])[0]))
                        # Convert to string. 0 -> "0", 1 -> "1", None -> "X" (invalid/unkown).
                        bitpos_value[bit_pos] = 'X' if data['value'] is None else str(data['value'])

                # sort metadata entries based on the bit position (descending), then concat them
                # in order s.t. lsb is rightmost (e.g., bit_N|bit_N-1|...|bit_1|bit_0)
                print(bitpos_value)
                out_data[abbrv] = ''.join([bitpos_value[k] for k in sorted(bitpos_value, reverse=True)])

        return out_data

    def extract_metadata(self, signals: dict) -> dict[str]:
        self.extracted_signals = True
        for signal_name, signal_dict in self.metadata.items():
            if signal_name in signals:
                self.metadata[signal_name]['value'] = int(signals[signal_name])
        return self.get_metadata()

    def extract_metadata_csv(self, column_names: list[str], csvfile_line: list):
        self.extracted_signals = True
        all_metadata = dict()
        cmds = self.cmds if self.is_two_cycle_cmd else [self]
        for line, dram_sub_cmd in zip(csvfile_line, cmds):
            md = dram_sub_cmd.extract_metadata({name: value for name, value in zip(column_names, line)})
            # merge dictionaries by 'name'
            for k, v in md.items():
                if k not in all_metadata:
                    all_metadata[k] = v
                else:
                    # e.g., to combine the row bits collected in the first and second cycle of ACT
                    all_metadata[k] = v + all_metadata[k]
        return all_metadata
