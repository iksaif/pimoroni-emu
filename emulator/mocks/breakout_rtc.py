"""Mock implementation of PCF85063A RTC breakout."""

import time as _time
from emulator.mocks.base import I2CSensorMock


class BreakoutRTC(I2CSensorMock):
    """PCF85063A real-time clock."""

    _component_name = "RTC"
    _default_address = 0x51

    def __init__(self, i2c, address=0x51):
        super().__init__(i2c, address)
        self._24hour = True
        self._alarm_flag = False

    def setup(self):
        pass

    def set_time(self, second, minute, hour, weekday, day, month, year):
        return True

    def set_24_hour(self):
        self._24hour = True

    def set_12_hour(self):
        self._24hour = False

    def is_12_hour(self):
        return not self._24hour

    def is_pm(self):
        return _time.localtime().tm_hour >= 12

    def update_time(self):
        return True

    def string_time(self):
        t = _time.localtime()
        return f"{t.tm_hour:02d}:{t.tm_min:02d}:{t.tm_sec:02d}"

    def string_date(self):
        t = _time.localtime()
        return f"{t.tm_mday:02d}/{t.tm_mon:02d}/{t.tm_year}"

    def enable_periodic_update_interrupt(self, enable):
        pass

    def read_periodic_update_interrupt_flag(self):
        return self._alarm_flag

    def clear_periodic_update_interrupt_flag(self):
        self._alarm_flag = False

    def get_unix(self):
        return int(_time.time())

    def set_unix(self, timestamp):
        pass

    def set_backup_switchover_mode(self, mode):
        pass

    def set_seconds(self, v): pass
    def set_minutes(self, v): pass
    def set_hours(self, v): pass
    def set_weekday(self, v): pass
    def set_date(self, v): pass
    def set_month(self, v): pass
    def set_year(self, v): pass
