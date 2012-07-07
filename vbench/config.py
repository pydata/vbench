import pytz

TIME_ZONE = pytz.timezone('US/Eastern')


def set_timezone(tz):
    global TIME_ZONE
    TIME_ZONE = tz
