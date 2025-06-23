import pint


class Units:
    def __init__(self):
        self.ureg = pint.UnitRegistry()
        self.ureg.define("micro- = 1e-6 = u-")

    def ns_to_sec_val(self, val: int) -> float:
        return (val * self.ureg.nanoseconds).to('seconds').magnitude

    def sec_to_ns(self, val: int) -> float:
        return (val * self.ureg.seconds).to('nanoseconds').magnitude

    def sec_to_us(self, val: int) -> float:
        return (val * self.ureg.seconds).to('microseconds').magnitude

    def ns_to_sec(self, val: int) -> str:
        return '{:.12f}'.format((val * self.ureg.nanoseconds).to('seconds').magnitude)

    def ps_to_sec(self, val: int) -> str:
        return '{:.12f}'.format((val * self.ureg.picoseconds).to('seconds').magnitude)

    def ps_to_sec_val(self, val: int) -> str:
        return (val * self.ureg.picoseconds).to('seconds').magnitude

    def ms_to_sec(self, val: int) -> str:
        return '{:.12f}'.format((val * self.ureg.milliseconds).to('seconds').magnitude)

    def us_to_sec(self, val: int) -> str:
        return '{:.12f}'.format((val * self.ureg.microseconds).to('seconds').magnitude)

    def us_to_sec_val(self, val: float) -> str:
        return (val * self.ureg.microseconds).to('seconds').magnitude

    def pp_sec(self, val: int, show_unit: bool = True):
        pu = (val * self.ureg.seconds).to_compact()
        # this is not ideal as it returns two different types: either a string or a value
        return f"{pu.magnitude:3.4f} {pu.units:~}" if show_unit else pu.magnitude
