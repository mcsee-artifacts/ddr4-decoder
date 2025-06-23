from .dram_command import DramCommand
from .enums import E_DRAM_CMD, E_DRAM_TYPE


class E_DDR4_DRAM_CMD(E_DRAM_CMD):
    mrs = "MRS"
    ref = "REF"
    sre = "SRE"
    srx = "SRX"
    pre = "PRE"
    prea = "PREA"
    rfu = "RFU"
    act = "ACT"
    wr = "WR"
    wrs4 = "WRS4"
    wrs8 = "WRS8"
    wra = "WRA"
    wras4 = "WRAS4"
    wras8 = "WRAS4"
    rd = "RD"
    rds4 = "RDS4"
    rds8 = "RDS8"
    rda = "RDA"
    rdas4 = "RDAS4"
    rdas8 = "RDAS8"
    nop = "NOP"
    des = "DES"
    pde = "PDE"
    pdx = "PDX"
    zqcl = "ZQCL"
    zqcs = "ZQCS"
    unknown = "unknown"


f_str_bk = "{:02b}"
f_str_bg = "{:02b}"
f_str_row = "{:18b}"

INSPECT_ROWS = False

if INSPECT_ROWS:
    # noinspection DuplicatedCode
    DDR4_DRAM_COMMANDS = [
        # ACTIVATE
        DramCommand(E_DRAM_TYPE.ddr4, E_DDR4_DRAM_CMD.act, { 'CS0_n': 0, 'ACT_n': 0, })
            .add_metadata("BG1", f_str_bg, "bankgroup bit 1", "bg")
            .add_metadata("BG0", f_str_bg, "bankgroup bit 0", "bg")
            .add_metadata("BA1", f_str_bk, "bank bit 1", "bk")
            .add_metadata("BA0", f_str_bk, "bank bit 0", "bk")
            .add_metadata("A17", f_str_row, "row bit 17", "row")
            .add_metadata("RAS_n", f_str_row, "row bit 16", "row")
            .add_metadata("CAS_n", f_str_row, "row bit 15", "row")
            .add_metadata("WE_n", f_str_row, "row bit 14", "row")
            .add_metadata("A13", f_str_row, "row bit 13", "row")
            .add_metadata("A12", f_str_row, "row bit 12", "row")
            .add_metadata("A11", f_str_row, "row bit 11", "row")
            .add_metadata("A10", f_str_row, "row bit 10", "row")
            .add_metadata("A9", f_str_row, "row bit 9", "row")
            .add_metadata("A8", f_str_row, "row bit 8", "row")
            .add_metadata("A7", f_str_row, "row bit 7", "row")
            .add_metadata("A6", f_str_row, "row bit 6", "row")
            .add_metadata("A5", f_str_row, "row bit 5", "row")
            .add_metadata("A4", f_str_row, "row bit 4", "row")
            .add_metadata("A3", f_str_row, "row bit 3", "row")
            .add_metadata("A2", f_str_row, "row bit 2", "row")
            .add_metadata("A1", f_str_row, "row bit 1", "row")
            .add_metadata("A0", f_str_row, "row bit 0", "row"),

        # This should allow us to see commands other than ACT as "unknown" in the decoded traces.
        DramCommand(E_DRAM_TYPE.ddr4, E_DDR4_DRAM_CMD.unknown, { 'CS0_n': 0, 'ACT_n': 1 })
    ]
else:
    # noinspection DuplicatedCode
    DDR4_DRAM_COMMANDS = [
        # MODE REGISTER SET
        DramCommand(E_DRAM_TYPE.ddr4, E_DDR4_DRAM_CMD.mrs,
            { 'CS0_n': 0, 'ACT_n': 1, 'RAS_n': 0, 'CAS_n': 0, 'WE_n': 0 }),

        # REFRESH
        DramCommand(E_DRAM_TYPE.ddr4, E_DDR4_DRAM_CMD.ref,
            { 'CS0_n': 0, 'ACT_n': 1, 'RAS_n': 0, 'CAS_n': 0, 'WE_n': 1 }),

        # PRECHARGE (includes PREA)
        DramCommand(E_DRAM_TYPE.ddr4, E_DDR4_DRAM_CMD.pre,
            { 'CS0_n': 0, 'ACT_n': 1, 'RAS_n': 0, 'CAS_n': 1, 'WE_n': 0 })
            .add_metadata("BG1", f_str_bg, "bankgroup bit 1", "bg")
            .add_metadata("BG0", f_str_bg, "bankgroup bit 0", "bg")
            .add_metadata("BA1", f_str_bk, "bank bit 1", "bk")
            .add_metadata("BA0", f_str_bk, "bank bit 0", "bk"),

        # RFU
        DramCommand(E_DRAM_TYPE.ddr4, E_DDR4_DRAM_CMD.rfu,
            { 'CS0_n': 0, 'ACT_n': 1, 'RAS_n': 0, 'CAS_n': 1, 'WE_n': 1 }),

        # ACTIVATE
        DramCommand(E_DRAM_TYPE.ddr4, E_DDR4_DRAM_CMD.act, { 'CS0_n': 0, 'ACT_n': 0, })
            .add_metadata("BG1", f_str_bg, "bankgroup bit 1", "bg")
            .add_metadata("BG0", f_str_bg, "bankgroup bit 0", "bg")
            .add_metadata("BA1", f_str_bk, "bank bit 1", "bk")
            .add_metadata("BA0", f_str_bk, "bank bit 0", "bk")
            .add_metadata("A17", f_str_row, "row bit 17", "row")
            .add_metadata("RAS_n", f_str_row, "row bit 16", "row")
            .add_metadata("CAS_n", f_str_row, "row bit 15", "row")
            .add_metadata("WE_n", f_str_row, "row bit 14", "row")
            .add_metadata("A13", f_str_row, "row bit 13", "row")
            .add_metadata("A12", f_str_row, "row bit 12", "row")
            .add_metadata("A11", f_str_row, "row bit 11", "row")
            .add_metadata("A10", f_str_row, "row bit 10", "row")
            .add_metadata("A9", f_str_row, "row bit 9", "row")
            .add_metadata("A8", f_str_row, "row bit 8", "row")
            .add_metadata("A7", f_str_row, "row bit 7", "row")
            .add_metadata("A6", f_str_row, "row bit 6", "row")
            .add_metadata("A5", f_str_row, "row bit 5", "row")
            .add_metadata("A4", f_str_row, "row bit 4", "row")
            .add_metadata("A3", f_str_row, "row bit 3", "row")
            .add_metadata("A2", f_str_row, "row bit 2", "row")
            .add_metadata("A1", f_str_row, "row bit 1", "row")
            .add_metadata("A0", f_str_row, "row bit 0", "row"),

        # WRITE
        DramCommand(E_DRAM_TYPE.ddr4, E_DDR4_DRAM_CMD.wr,
            { 'CS0_n': 0, 'ACT_n': 1, 'RAS_n': 1, 'CAS_n': 0, 'WE_n': 0 })
            .add_metadata("BG1", f_str_bg, "bankgroup bit 1", "bg")
            .add_metadata("BG0", f_str_bg, "bankgroup bit 0", "bg")
            .add_metadata("BA1", f_str_bk, "bank bit 1", "bk")
            .add_metadata("BA0", f_str_bk, "bank bit 0", "bk"),

        # READ
        DramCommand(E_DRAM_TYPE.ddr4, E_DDR4_DRAM_CMD.rd,
            { 'CS0_n': 0, 'ACT_n': 1, 'RAS_n': 1, 'CAS_n': 0, 'WE_n': 1 })
            .add_metadata("BG1", f_str_bg, "bankgroup bit 1", "bg")
            .add_metadata("BG0", f_str_bg, "bankgroup bit 0", "bg")
            .add_metadata("BA1", f_str_bk, "bank bit 1", "bk")
            .add_metadata("BA0", f_str_bk, "bank bit 0", "bk"),
    ]
