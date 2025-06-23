from dataclasses import dataclass

from util.dram_command import E_DRAM_CMD


@dataclass
class DecodedCommand:
    timestamp_sec: str
    cmd: str
    # bankgroup bits
    bg: str
    # bank bits
    bk: str
    # row bits
    row: str
    # column bits
    col: str
    # cycle count since start of CSV file
    cycle: int

    def __init__(self, timestamp_sec: str, cmd: E_DRAM_CMD, metadata: dict, cycle: int):
        self.timestamp_sec = timestamp_sec
        self.cmd = cmd.name
        self.bg = metadata.get('bg', '')
        self.bk = metadata.get('bk', '')
        self.row = metadata.get('row', '')
        self.col = metadata.get('col', '')
        self.cycle = cycle

    @staticmethod
    def get_csv_header():
        return "timestamp_sec,cmd,bg,bk,row,col"

    def to_csv(self, newline: bool) -> str:
        out_str = ",".join([self.timestamp_sec, self.cmd, self.bg, self.bk, self.row, self.col])
        return out_str + "\n" if newline else out_str

    def __eq__(self, other) -> bool:
        if isinstance(other, DecodedCommand):
            return self.timestamp_sec == other.timestamp_sec \
                and self.cmd == other.cmd \
                and self.bg == other.bg \
                and self.bk == other.bk \
                and self.row == other.row \
                and self.col == other.col
        # if other is not a DecodedCommand
        return False

    def equals(self, other, ignore_timestamp: bool = True) -> bool:
        other_ts_bak = other.timestamp_sec
        if ignore_timestamp:
            other.timestamp_sec = self.timestamp_sec
        result = (self == other)
        other.timestamp_sec = other_ts_bak
        return result


