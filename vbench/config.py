import pytz, sys

TIME_ZONE = pytz.timezone('US/Eastern')


def set_timezone(tz):
    global TIME_ZONE
    TIME_ZONE = tz

def is_interactive():
    """Return True if all in/outs are tty"""
    return sys.stdin.isatty() and sys.stdout.isatty() and sys.stderr.isatty()

