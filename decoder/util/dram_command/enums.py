from enum import Enum


class E_DRAM_TYPE(Enum):
    ddr4 = "DDR4"
    ddr5 = "DDR5"


# This enum is inherited from by type-specific enums like E_DDR5_DRAM_CMD.
class E_DRAM_CMD(Enum):
    pass
