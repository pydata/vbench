#!/usr/bin/python
#emacs: -*- mode: python-mode; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*- 
#ex: set sts=4 ts=4 sw=4 noet:
"""
 COPYRIGHT: Yaroslav Halchenko 2013

 LICENSE: MIT

  Permission is hereby granted, free of charge, to any person obtaining a copy
  of this software and associated documentation files (the "Software"), to deal
  in the Software without restriction, including without limitation the rights
  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
  copies of the Software, and to permit persons to whom the Software is
  furnished to do so, subject to the following conditions:

  The above copyright notice and this permission notice shall be included in
  all copies or substantial portions of the Software.

  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
  THE SOFTWARE.
"""

__author__ = 'Yaroslav Halchenko'
__copyright__ = 'Copyright (c) 2013 Yaroslav Halchenko'
__license__ = 'MIT'

import logging, os, sys

from vbench.config import is_interactive

# For additional metrics optionally to add to debug messages
from os import getpid
try:
    import psutil
    _process = psutil.Process(getpid())
except ImportError:
    psutil = None

# Recipe from http://stackoverflow.com/questions/384076/how-can-i-color-python-logging-output
# by Brandon Thomson
# Adjusted for automagic determination either coloring is needed and
# prefixing of multiline log lines
class ColorFormatter(logging.Formatter):

  FORMAT = ("$BOLD%(asctime)-15s$RESET [%(levelname)s] "
            "%(message)s "
            "($BOLD%(filename)s$RESET:%(lineno)d)")

  BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)

  RESET_SEQ = "\033[0m"
  COLOR_SEQ = "\033[1;%dm"
  BOLD_SEQ = "\033[1m"

  COLORS = {
    'WARNING': YELLOW,
    'INFO': WHITE,
    'DEBUG': BLUE,
    'CRITICAL': YELLOW,
    'ERROR': RED
  }

  def __init__(self, use_color=None, metrics=[]):
    if use_color is None:
      # if 'auto' - use color only if all streams are tty
      use_color = is_interactive()
    self.metrics = [m for m in metrics if m]
    self._peak_rss = self._peak_vms = 0
    msg = self.formatter_msg(self.FORMAT, use_color)
    logging.Formatter.__init__(self, msg)
    self.use_color = use_color

  def get_pid(self):
    return "pid=%d" % (getpid())

  def get_vmem(self):
    if not psutil:
      return "install psutil for vmem"
    mi = _process.get_memory_info()
    # in later versions of psutil mi is a named tuple.
    # but that is not the case on Debian squeeze with psutil 0.1.3
    rss = mi[0] / 1024
    vms = mi[1] / 1024
    self._peak_rss = max(rss, self._peak_rss)
    self._peak_vms = max(vms, self._peak_vms)
    return "VMS=%d/%d RSS=%d/%d" % (vms, self._peak_vms, rss, self._peak_rss)

  def formatter_msg(self, fmt, use_color=False):
    if use_color:
      fmt = fmt.replace("$RESET", self.RESET_SEQ).replace("$BOLD", self.BOLD_SEQ)
    else:
      fmt = fmt.replace("$RESET", "").replace("$BOLD", "")
    return fmt

  def format(self, record):
    levelname = record.levelname
    if self.use_color:
      # BLUE would also be for the custom levels for now
      fore_color = 30 + self.COLORS.get(levelname, self.BLUE)
      levelname_color = self.COLOR_SEQ % fore_color + "%-7s" % levelname + self.RESET_SEQ
      record.levelname = levelname_color
      metric_color, off_color = self.COLOR_SEQ % self.RED, self.RESET_SEQ
    else:
      metric_color, off_color = '', ''
    record.msg = record.msg.replace("\n", "\n| ")
    for metric in self.metrics:
      record.msg = "[" + metric_color \
        + getattr(self, 'get_%s' % metric)() \
        + off_color + "] " + record.msg
    return logging.Formatter.format(self, record)

def set_loglevel(log, level=None):
    # And allow to control it from the environment
    if level is None:
        level = os.environ.get('VBENCH_LOGLEVEL', 'INFO')
    level_value = None
    try: # might be int
        level_value = int(level)
    except:
        # or symbolic name known to logging
        try:
            level_value = getattr(logging, level)
        except:
            pass
    if level_value is None:
        log.setLevel(logging.INFO)        # set default
        log.warning("Could not deduce logging level from VBENCH_LOGLEVEL=%r" % level)
    else:
        log.setLevel(level_value)

# Setup default vbench logging

# By default mimic previously talkative behavior
log = logging.getLogger('vb')
set_loglevel(log)
_log_handler = logging.StreamHandler(sys.stdout)


# But now improve with colors and useful information such as time
_log_handler.setFormatter(
  ColorFormatter(metrics=os.environ.get('VBENCH_LOGMETRICS', '').split(',')))

if log.getEffectiveLevel() < logging.DEBUG \
    and 'vmem' in _log_handler.formatter.metrics:
    # for it to be useful we should decorate builtin gc to report
    # memory when gc gets enabled/disabled
    import gc
    _orig_gc_enable, _orig_gc_disable = gc.enable, gc.disable
    def _gc_enable():
        log.log(5, "Enabling GC")
        _orig_gc_enable()
    gc.enable = _gc_enable

    def _gc_disable():
        log.log(5, "Disabling GC")
        _orig_gc_disable()
    gc.disable = _gc_disable

#logging.Formatter('%(asctime)-15s %(levelname)-6s %(message)s'))
log.addHandler(_log_handler)

