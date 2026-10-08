"""Business dates are independent of the server's operating-system timezone."""

import os
from datetime import datetime
from zoneinfo import ZoneInfo


def business_now():
    return datetime.now(ZoneInfo(os.getenv("BUSINESS_TIMEZONE", "America/Sao_Paulo")))


def business_today():
    return business_now().date()
