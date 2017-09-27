#!/usr/bin/env python
import os
import sys
import ctypes
import textwrap
import re
import urllib
import click
import unicodedata
import string
from pprint import pprint as pp
from collections import namedtuple

from tvoverlord.config import Config
from tvoverlord.util import U


def hash2magnet(magnet_hash, title):
    magnet_url = 'magnet:?xt=urn:btih:{}&dn={}'
    magnet = magnet_url.format(magnet_hash, urllib.parse.quote(title))
    return magnet


def sxxexx(season='', episode=''):
    """Return a season and episode formated as S01E01"""
    se = ''
    if season and episode:
        season = int(season)
        episode = int(episode)
        se = 'S%02dE%02d' % (season, episode)
    return se


def sxee(season='', episode=''):
    """Return a season and episode formated as 1X01"""
    se = ''
    if season and episode:
        season = int(season)
        episode = int(episode)
        se = '%dX%02d' % (season, episode)
    return se


def style(text, fg=None, bg=None, bold=None, strike=None, ul=None):
    if Config.is_win:
        fancy = click.style(text, fg=fg, bg=bg, bold=bold, underline=ul)
    else:
        fancy = U.style(text, fg=fg, bg=bg, bold=bold, strike=strike, ul=ul)
    return fancy


def dict_factory(cursor, row):
    """Changes the data returned from the db from a
    tupple to a dictionary"""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def format_paragraphs(msg, indent=''):
    if not msg:
        return ''
    paragraphs = re.split('\n\n+', msg)
    for i, paragraph in enumerate(paragraphs):
        paragraph = textwrap.dedent(paragraph).strip()
        paragraph = textwrap.fill(
            paragraph,
            initial_indent=indent,
            subsequent_indent=indent)
        paragraphs[i] = paragraph
    document = '\n\n'.join(paragraphs)
    return document


class FancyPrint:
    def __init__(self):
        self.bs = '\b' * Config.console_columns

    def standard_print(self, msg):
        msg = '\n'.join([i.ljust(Config.console_columns) for i in msg.split('\n')])
        msg = msg + '\n'
        self._back_print(msg)

    def done(self, msg=''):
        msg = msg.ljust(Config.console_columns)
        sys.stdout.write('\033[F')
        self._back_print(msg)

    def _back_print(self, msg):
        full_msg = '%s%s' % (self.bs, msg)

        sys.stdout.write(full_msg)
        sys.stdout.flush()


# http://stackoverflow.com/a/6397492
def disk_info(path):
    """Return disk usage associated with path."""
    if Config.is_win:
        free_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(
            ctypes.c_wchar_p(path), None, None,
            ctypes.pointer(free_bytes))
        return free_bytes.value
    else:
        st = os.statvfs(path)
        free = (st.f_bavail * st.f_frsize)
        total = (st.f_blocks * st.f_frsize)
        used = (st.f_blocks - st.f_bfree) * st.f_frsize
        try:
            percent = ret = (float(used) / total) * 100
        except ZeroDivisionError:
            percent = 0
        # NB: the percentage is -5% than what shown by df due to
        # reserved blocks that we are currently not considering:
        # http://goo.gl/sWGbH
        usage_ntuple = namedtuple('usage',  'total used free percent')
        # return usage_ntuple(total, used, free, round(percent, 1))
        return free


def itemize(shows):
    depth = len(str(len(shows))) + 1
    for i, show in enumerate(shows):
        i = i + 1
        number = '%s.' % i
        number = number.rjust(depth)
        click.echo('  %s %s' % (number, show.seriesname))


def clean_filename(fname, strict=False):
    if strict:
        valid_chars = '-_.(){alpha}{nums}'.format(
            alpha=string.ascii_letters, nums=string.digits)
    else:
        valid_chars = '-_.()[] {alpha}{nums}'.format(
            alpha=string.ascii_letters, nums=string.digits)
    fname = unicodedata.normalize('NFKD', fname)
    clean = ''.join(c for c in fname if c in valid_chars)
    return clean


if __name__ == '__main__':
    pass
