"""Freeze "now" for fixture renders, so demo.html only changes when the code does.

Import before loading a script: the scripts read datetime.now()/date.today(),
some at import time and some inside gen_html.
"""
import datetime as _real
import sys
import types

AS_OF = (2026, 11, 5)


class _Datetime(_real.datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(*AS_OF, 12, tzinfo=tz)

    @classmethod
    def today(cls):
        return cls(*AS_OF, 12)


class _Date(_real.date):
    @classmethod
    def today(cls):
        return cls(*AS_OF)


frozen = types.ModuleType('datetime')
frozen.__dict__.update({k: v for k, v in vars(_real).items() if not k.startswith('__')})
frozen.datetime, frozen.date = _Datetime, _Date
sys.modules['datetime'] = frozen
