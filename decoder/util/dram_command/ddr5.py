from .dram_command import DramCommand
from .enums import E_DRAM_CMD, E_DRAM_TYPE


class E_DDR5_DRAM_CMD(E_DRAM_CMD):
    act = "ACT"
    act1 = "ACT1"
    act2 = "ACT2"
    pre_ab = "PREab"
    pre_sb = "PREsb"
    pre_pb = "PREpb"
    ref_ab = "REFab"
    ref_sb = "REFsb"
    rfm_sb = "RFMsb"
    rfm_ab = "RFMab"
    wr = "WR"
    wr1 = "WR1"
    wr2 = "WR2"
    wra = "WRA"
    wra1 = "WRA1"
    wra2 = "WRA2"
    rd = "RD"
    rd1 = "RD1"
    rd2 = "RD2"
    rda = "RDA"
    rda1 = "RDA1"
    rda2 = "RDA2"
    nop_pdx = "NOP/PDX"
    mpc = "MPC"
    pde = "PDE"
    sre = "SRE"
    sre_f = "SREF"
    rfu1c = "RFU1C"  # 1-cycle RFU
    rfu = "RFU"
    rfu1 = "RFU1"
    rfu2 = "RFU2"
    vref_ca = "VrefCA"
    vref_cs = "VrefCS"
    mrr = "MRR"
    mrr1 = "MRR1"
    mrr2 = "MRR2"
    mrw = "MRW"
    mrw1 = "MRW1"
    mrw2 = "MRW2"


f_str_bk = "{:02b}"
f_str_bg = "{:03b}"
f_str_row = "{:17b}"
f_str_opcode = "{:08b}"
f_str_col = "{:09b}"
f_str_mra = "{:08b}"


# noinspection DuplicatedCode
DDR5_DRAM_COMMANDS = [
    # ===================================================
    # ==== 1-CYCLE COMMANDS =============================
    # ===================================================

    # REFRESH
    DramCommand(E_DRAM_TYPE.ddr5, E_DDR5_DRAM_CMD.ref_ab,
                {'CS': 0, 'CA0': 1, 'CA1': 1, 'CA2': 0, 'CA3': 0, 'CA4': 1, 'CA9': 1, 'CA10': 0}, []),
    DramCommand(E_DRAM_TYPE.ddr5, E_DDR5_DRAM_CMD.ref_sb,
                {'CS': 0, 'CA0': 1, 'CA1': 1, 'CA2': 0, 'CA3': 0, 'CA4': 1, 'CA9': 1, 'CA10': 1}, [])
    .add_metadata("CA7", f_str_bk, "bank bit 1", "bk")
    .add_metadata("CA6", f_str_bk, "bank bit 0", "bk"),

    # REFRESH MANAGEMENT
    DramCommand(E_DRAM_TYPE.ddr5, E_DDR5_DRAM_CMD.rfm_ab,
                {'CS': 0, 'CA0': 1, 'CA1': 1, 'CA2': 0, 'CA3': 0, 'CA4': 1, 'CA9': 0, 'CA10': 0}, []),
    DramCommand(E_DRAM_TYPE.ddr5, E_DDR5_DRAM_CMD.rfm_sb,
                {'CS': 0, 'CA0': 1, 'CA1': 1, 'CA2': 0, 'CA3': 0, 'CA4': 1, 'CA9': 0, 'CA10': 1}, [])
    .add_metadata("CA7", f_str_bk, "bank bit 1", "bk")
    .add_metadata("CA6", f_str_bk, "bank bit 0", "bk"),

    # PRECHARGE
    DramCommand(E_DRAM_TYPE.ddr5, E_DDR5_DRAM_CMD.pre_ab,
                {'CS': 0, 'CA0': 1, 'CA1': 1, 'CA2': 0, 'CA3': 1, 'CA4': 0, 'CA10': 0}, []),
    DramCommand(E_DRAM_TYPE.ddr5, E_DDR5_DRAM_CMD.pre_sb,
                {'CS': 0, 'CA0': 1, 'CA1': 1, 'CA2': 0, 'CA3': 1, 'CA4': 0, 'CA10': 1}, [])
    .add_metadata("CA7", f_str_bk, "bank bit 1", "bk")
    .add_metadata("CA6", f_str_bk, "bank bit 0", "bk"),
    DramCommand(E_DRAM_TYPE.ddr5, E_DDR5_DRAM_CMD.pre_pb,
                {'CS': 0, 'CA0': 1, 'CA1': 1, 'CA2': 0, 'CA3': 1, 'CA4': 1}, [])
    .add_metadata("CA7", f_str_bk, "bank bit 1", "bk")
    .add_metadata("CA6", f_str_bk, "bank bit 0", "bk")
    .add_metadata("CA10", f_str_bg, "bankgroup bit 2", "bg")
    .add_metadata("CA9", f_str_bg, "bankgroup bit 1", "bg")
    .add_metadata("CA8", f_str_bg, "bankgroup bit 0", "bg"),

    # NO OPERATION or POWER-DOWN EXIT
    DramCommand(E_DRAM_TYPE.ddr5, E_DDR5_DRAM_CMD.nop_pdx,
                {'CS': 0, 'CA0': 1, 'CA1': 1, 'CA2': 1, 'CA3': 1, 'CA4': 1}, []),

    # MULTI-PURPOSE COMMAND
    DramCommand(E_DRAM_TYPE.ddr5, E_DDR5_DRAM_CMD.mpc,
                {'CS': 0, 'CA0': 1, 'CA1': 1, 'CA2': 1, 'CA3': 1, 'CA4': 0}, [])
    .add_metadata("CA12", f_str_opcode, "opcode bit 7", "opc")
    .add_metadata("CA11", f_str_opcode, "opcode bit 6", "opc")
    .add_metadata("CA10", f_str_opcode, "opcode bit 5", "opc")
    .add_metadata("CA9", f_str_opcode, "opcode bit 4", "opc")
    .add_metadata("CA8", f_str_opcode, "opcode bit 3", "opc")
    .add_metadata("CA7", f_str_opcode, "opcode bit 2", "opc")
    .add_metadata("CA6", f_str_opcode, "opcode bit 1", "opc")
    .add_metadata("CA5", f_str_opcode, "opcode bit 0", "opc"),

    # POWER-DOWN ENTRY
    DramCommand(E_DRAM_TYPE.ddr5, E_DDR5_DRAM_CMD.pde,
                {'CS': 0, 'CA0': 1, 'CA1': 1, 'CA2': 1, 'CA3': 0, 'CA4': 1, 'CA10': 1}, []),

    # SELF-REFRESH ENTRY
    DramCommand(E_DRAM_TYPE.ddr5, E_DDR5_DRAM_CMD.sre,
                {'CS': 0, 'CA0': 1, 'CA1': 1, 'CA2': 1, 'CA3': 0, 'CA4': 1, 'CA9': 1, 'CA10': 0}, []),

    # SELF-REFRESH ENTRY with FREQUENCY CHANGE
    DramCommand(E_DRAM_TYPE.ddr5, E_DDR5_DRAM_CMD.sre_f,
                {'CS': 0, 'CA0': 1, 'CA1': 1, 'CA2': 1, 'CA3': 0, 'CA4': 1, 'CA9': 0, 'CA10': 0}, []),

    # RESERVED FOR FUTURE USE (RFU)
    DramCommand(E_DRAM_TYPE.ddr5, E_DDR5_DRAM_CMD.rfu1c,
                {'CS': 0, 'CA0': 1, 'CA1': 1, 'CA2': 1, 'CA3': 0, 'CA4': 0}, []),

    # VrefCA
    DramCommand(E_DRAM_TYPE.ddr5, E_DDR5_DRAM_CMD.vref_ca,
                {'CS': 0, 'CA0': 1, 'CA1': 1, 'CA2': 0, 'CA3': 0, 'CA4': 0, 'CA12': 0}, []),

    # VrefCS
    DramCommand(E_DRAM_TYPE.ddr5, E_DDR5_DRAM_CMD.vref_cs,
                {'CS': 0, 'CA0': 1, 'CA1': 1, 'CA2': 0, 'CA3': 0, 'CA4': 0, 'CA12': 1}, []),

    # ===================================================
    # ==== 2-CYCLE COMMANDS =============================
    # ---------------------------------------------------
    # All 2-cycle commands have in common that they
    # require CS==1 in the second (subsequent) cycle.
    # ===================================================

    # BANK ACTIVATE
    DramCommand.as_two_cycle_cmd(
        E_DDR5_DRAM_CMD.act, [
            DramCommand(E_DRAM_TYPE.ddr5, E_DDR5_DRAM_CMD.act1, {'CS': 0, 'CA0': 0, 'CA1': 0}, [])
            .add_metadata("CA7", f_str_bk, "bank bit 1", "bk")
            .add_metadata("CA6", f_str_bk, "bank bit 0", "bk")
            .add_metadata("CA10", f_str_bg, "bankgroup bit 2", "bg")
            .add_metadata("CA9", f_str_bg, "bankgroup bit 1", "bg")
            .add_metadata("CA8", f_str_bg, "bankgroup bit 0", "bg")
            .add_metadata("CA5", f_str_row, "row bit 3", "row")
            .add_metadata("CA4", f_str_row, "row bit 2", "row")
            .add_metadata("CA3", f_str_row, "row bit 1", "row")
            .add_metadata("CA2", f_str_row, "row bit 0", "row"),

            DramCommand(E_DRAM_TYPE.ddr5, E_DDR5_DRAM_CMD.act2, {'CS': 1}, [])
            # .add_metadata("CA12", f_str_row, "row bit 16", "row")
            .add_metadata("CA11", f_str_row, "row bit 15", "row")
            .add_metadata("CA10", f_str_row, "row bit 14", "row")
            .add_metadata("CA9", f_str_row, "row bit 13", "row")
            .add_metadata("CA8", f_str_row, "row bit 12", "row")
            .add_metadata("CA7", f_str_row, "row bit 11", "row")
            .add_metadata("CA6", f_str_row, "row bit 10", "row")
            .add_metadata("CA5", f_str_row, "row bit 9", "row")
            .add_metadata("CA4", f_str_row, "row bit 8", "row")
            .add_metadata("CA3", f_str_row, "row bit 7", "row")
            .add_metadata("CA2", f_str_row, "row bit 6", "row")
            .add_metadata("CA1", f_str_row, "row bit 5", "row")
            .add_metadata("CA0", f_str_row, "row bit 4", "row"),
        ]
    ),

    # WRITE
    DramCommand.as_two_cycle_cmd(
        E_DDR5_DRAM_CMD.wr, [
            DramCommand(E_DRAM_TYPE.ddr5, E_DDR5_DRAM_CMD.wr1, {'CS': 0, 'CA0': 1, 'CA1': 0, 'CA2': 1, 'CA3': 1, 'CA4': 0}, [])
            # bank bits
            .add_metadata("CA7", f_str_bk, "bank bit 1", "bk")
            .add_metadata("CA6", f_str_bk, "bank bit 0", "bk")
            # bank group bits
            .add_metadata("CA10", f_str_bg, "bankgroup bit 2", "bg")
            .add_metadata("CA9", f_str_bg, "bankgroup bit 1", "bg")
            .add_metadata("CA8", f_str_bg, "bankgroup bit 0", "bg"),
            DramCommand(E_DRAM_TYPE.ddr5, E_DDR5_DRAM_CMD.wr2, {'CS': 1, 'CA10': 1}, [])  # not sure about CA11: WR_Partial=L
            .add_metadata("CA8", f_str_col, "column bit 10", "col")
            .add_metadata("CA7", f_str_col, "column bit 9", "col")
            .add_metadata("CA6", f_str_col, "column bit 8", "col")
            .add_metadata("CA5", f_str_col, "column bit 7", "col")
            .add_metadata("CA4", f_str_col, "column bit 6", "col")
            .add_metadata("CA3", f_str_col, "column bit 5", "col")
            .add_metadata("CA2", f_str_col, "column bit 4", "col")
            .add_metadata("CA1", f_str_col, "column bit 3", "col")
            .add_metadata("CA0", f_str_col, "column bit 2", "col")
        ]
    ),

    # WRITE with AUTO-PRECHARGE
    # WRA is the same as WR except for CA10 being 0 in the second cycle
    DramCommand.as_two_cycle_cmd(
        E_DDR5_DRAM_CMD.wra, [
            DramCommand(E_DRAM_TYPE.ddr5, E_DDR5_DRAM_CMD.wra1, {'CS': 0, 'CA0': 1, 'CA1': 0, 'CA2': 1, 'CA3': 1, 'CA4': 0}, [])
            # bank bits
            .add_metadata("CA7", f_str_bk, "bank bit 1", "bk")
            .add_metadata("CA6", f_str_bk, "bank bit 0", "bk")
            # bank group bits
            .add_metadata("CA10", f_str_bg, "bankgroup bit 2", "bg")
            .add_metadata("CA9", f_str_bg, "bankgroup bit 1", "bg")
            .add_metadata("CA8", f_str_bg, "bankgroup bit 0", "bg"),
            DramCommand(E_DRAM_TYPE.ddr5, E_DDR5_DRAM_CMD.wra2, {'CS': 1, 'CA10': 0}, [])
            .add_metadata("CA8", f_str_col, "column bit 10", "col")
            .add_metadata("CA7", f_str_col, "column bit 9", "col")
            .add_metadata("CA6", f_str_col, "column bit 8", "col")
            .add_metadata("CA5", f_str_col, "column bit 7", "col")
            .add_metadata("CA4", f_str_col, "column bit 6", "col")
            .add_metadata("CA3", f_str_col, "column bit 5", "col")
            .add_metadata("CA2", f_str_col, "column bit 4", "col")
            .add_metadata("CA1", f_str_col, "column bit 3", "col")
            .add_metadata("CA0", f_str_col, "column bit 2", "col")
        ]
    ),

    # READ
    DramCommand.as_two_cycle_cmd(
        E_DDR5_DRAM_CMD.rd, [
            DramCommand(E_DRAM_TYPE.ddr5, E_DDR5_DRAM_CMD.rd1, {'CS': 0, 'CA0': 1, 'CA1': 0, 'CA2': 1, 'CA3': 1, 'CA4': 1}, [])
            # bank bits
            .add_metadata("CA7", f_str_bk, "bank bit 1", "bk")
            .add_metadata("CA6", f_str_bk, "bank bit 0", "bk")
            # bank group bits
            .add_metadata("CA10", f_str_bg, "bankgroup bit 2", "bg")
            .add_metadata("CA9", f_str_bg, "bankgroup bit 1", "bg")
            .add_metadata("CA8", f_str_bg, "bankgroup bit 0", "bg"),
            DramCommand(E_DRAM_TYPE.ddr5, E_DDR5_DRAM_CMD.rd2, {'CS': 1, 'CA10': 1}, [])
            .add_metadata("CA8", f_str_col, "column bit 10", "col")
            .add_metadata("CA7", f_str_col, "column bit 9", "col")
            .add_metadata("CA6", f_str_col, "column bit 8", "col")
            .add_metadata("CA5", f_str_col, "column bit 7", "col")
            .add_metadata("CA4", f_str_col, "column bit 6", "col")
            .add_metadata("CA3", f_str_col, "column bit 5", "col")
            .add_metadata("CA2", f_str_col, "column bit 4", "col")
            .add_metadata("CA1", f_str_col, "column bit 3", "col")
            .add_metadata("CA0", f_str_col, "column bit 2", "col")
        ]
    ),

    # READ WITH AUTO PRECHARGE
    DramCommand.as_two_cycle_cmd(
        E_DDR5_DRAM_CMD.rda, [
            DramCommand(E_DRAM_TYPE.ddr5, E_DDR5_DRAM_CMD.rda1, {'CS': 0, 'CA0': 1, 'CA1': 0, 'CA2': 1, 'CA3': 1, 'CA4': 1}, [])
            # bank bits
            .add_metadata("CA7", f_str_bk, "bank bit 1", "bk")
            .add_metadata("CA6", f_str_bk, "bank bit 0", "bk")
            # bank group bits
            .add_metadata("CA10", f_str_bg, "bankgroup bit 2", "bg")
            .add_metadata("CA9", f_str_bg, "bankgroup bit 1", "bg")
            .add_metadata("CA8", f_str_bg, "bankgroup bit 0", "bg"),
            DramCommand(E_DRAM_TYPE.ddr5, E_DDR5_DRAM_CMD.rda2, {'CS': 1, 'CA10': 0}, [])
            .add_metadata("CA8", f_str_col, "column bit 10", "col")
            .add_metadata("CA7", f_str_col, "column bit 9", "col")
            .add_metadata("CA6", f_str_col, "column bit 8", "col")
            .add_metadata("CA5", f_str_col, "column bit 7", "col")
            .add_metadata("CA4", f_str_col, "column bit 6", "col")
            .add_metadata("CA3", f_str_col, "column bit 5", "col")
            .add_metadata("CA2", f_str_col, "column bit 4", "col")
            .add_metadata("CA1", f_str_col, "column bit 3", "col")
            .add_metadata("CA0", f_str_col, "column bit 2", "col")
        ]
    ),

    # MODE-REGISTER READ
    DramCommand.as_two_cycle_cmd(
        E_DDR5_DRAM_CMD.mrr, [
            DramCommand(E_DRAM_TYPE.ddr5, E_DDR5_DRAM_CMD.mrr1, {'CS': 0, 'CA0': 1, 'CA1': 0, 'CA2': 1, 'CA3': 0, 'CA4': 1}, [])
            .add_metadata("CA12", f_str_mra, "machine register address bit 7", "mra")
            .add_metadata("CA11", f_str_mra, "machine register address bit 6", "mra")
            .add_metadata("CA10", f_str_mra, "machine register address bit 5", "mra")
            .add_metadata("CA9", f_str_mra, "machine register address bit 4", "mra")
            .add_metadata("CA8", f_str_mra, "machine register address bit 3", "mra")
            .add_metadata("CA7", f_str_mra, "machine register address bit 2", "mra")
            .add_metadata("CA6", f_str_mra, "machine register address bit 1", "mra")
            .add_metadata("CA5", f_str_mra, "machine register address bit 0", "mra"),
            DramCommand(E_DRAM_TYPE.ddr5, E_DDR5_DRAM_CMD.mrr2, {'CS': 1, 'CA0': 0, 'CA1': 0}, [])
        ]
    ),

    # MODE-REGISTER WRITE
    DramCommand.as_two_cycle_cmd(
        E_DDR5_DRAM_CMD.mrw, [
            DramCommand(E_DRAM_TYPE.ddr5, E_DDR5_DRAM_CMD.mrw1, {'CS': 0, 'CA0': 1, 'CA1': 0, 'CA2': 1, 'CA3': 0, 'CA4': 0}, [])
            .add_metadata("CA12", f_str_mra, "machine register address bit 7", "mra")
            .add_metadata("CA11", f_str_mra, "machine register address bit 6", "mra")
            .add_metadata("CA10", f_str_mra, "machine register address bit 5", "mra")
            .add_metadata("CA9", f_str_mra, "machine register address bit 4", "mra")
            .add_metadata("CA8", f_str_mra, "machine register address bit 3", "mra")
            .add_metadata("CA7", f_str_mra, "machine register address bit 2", "mra")
            .add_metadata("CA6", f_str_mra, "machine register address bit 1", "mra")
            .add_metadata("CA5", f_str_mra, "machine register address bit 0", "mra"),
            DramCommand(E_DRAM_TYPE.ddr5, E_DDR5_DRAM_CMD.mrw2, {'CS': 1}, [])
            .add_metadata("CA7", f_str_opcode, "opcode bit 7", "opc")
            .add_metadata("CA6", f_str_opcode, "opcode bit 6", "opc")
            .add_metadata("CA5", f_str_opcode, "opcode bit 5", "opc")
            .add_metadata("CA4", f_str_opcode, "opcode bit 4", "opc")
            .add_metadata("CA3", f_str_opcode, "opcode bit 3", "opc")
            .add_metadata("CA2", f_str_opcode, "opcode bit 2", "opc")
            .add_metadata("CA1", f_str_opcode, "opcode bit 1", "opc")
            .add_metadata("CA0", f_str_opcode, "opcode bit 0", "opc")
        ]
    ),

    # RFU1
    DramCommand.as_two_cycle_cmd(
        E_DDR5_DRAM_CMD.rfu, [
            DramCommand(E_DRAM_TYPE.ddr5, E_DDR5_DRAM_CMD.rfu1, {'CS': 0, 'CA0': 1, 'CA1': 0, 'CA2': 0, 'CA3': 0, 'CA4': 0}, []),
            DramCommand(E_DRAM_TYPE.ddr5, E_DDR5_DRAM_CMD.rfu2, {'CS': 1}, [])
        ]
    ),

    # RFU2
    DramCommand.as_two_cycle_cmd(
        E_DDR5_DRAM_CMD.rfu, [
            DramCommand(E_DRAM_TYPE.ddr5, E_DDR5_DRAM_CMD.rfu1, {'CS': 0, 'CA0': 1, 'CA1': 0, 'CA2': 0, 'CA3': 0, 'CA4': 1}, []),
            DramCommand(E_DRAM_TYPE.ddr5, E_DDR5_DRAM_CMD.rfu2, {'CS': 1}, [])
        ]
    ),

    # RFU3
    DramCommand.as_two_cycle_cmd(
        E_DDR5_DRAM_CMD.rfu, [
            DramCommand(E_DRAM_TYPE.ddr5, E_DDR5_DRAM_CMD.rfu1, {'CS': 0, 'CA0': 1, 'CA1': 0, 'CA2': 0, 'CA3': 1, 'CA4': 1}, []),
            DramCommand(E_DRAM_TYPE.ddr5, E_DDR5_DRAM_CMD.rfu2, {'CS': 1}, [])
        ]
    ),
]
