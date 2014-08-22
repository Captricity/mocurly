import pytz
import datetime

def current_time():
    return datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
