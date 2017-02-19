#!/usr/bin/env python

import urllib.request, urllib.parse, urllib.error
from time import mktime
from datetime import datetime
from pprint import pprint as pp
import click
import socket

import feedparser

from tvoverlord.util import U
from tvoverlord.config import Config


class Provider(object):

    name = 'ExtraTorrent'
    shortname = 'ET'
    url = ''
    provider_urls = [
        'http://extratorrent.cc',
        'http://etmirror.com',
        'http://etproxy.com',

        'https://extratorrent.unblocked.pe',
        'https://extratorrent.unblocked.la',
        'http://extratorrentonline.com',
        'http://extratorrent.works',
        'http://extratorrentlive.com',
        #'http://195.144.21.16/'
    ]

    @staticmethod
    def se_ep (season, episode, show_title):
        season_just = str (season).rjust (2, '0')
        episode = str (episode).rjust (2, '0')
        fixed = '%s S%sE%s' % (
            show_title, season_just, episode)
        return fixed

    def search(self, search_string, season=False, episode=False):
        if season and episode:
            search_string = '%s' % (
                self.se_ep(
                    season, episode, search_string))

        query = search_string
        encoded_search = urllib.parse.quote(query)

        socket.setdefaulttimeout(Config.timeout)
        show_data = []
        for try_url in self.provider_urls:
            # cid=0 everything, cid=8 tv shows:
            lookfor = 0
            if season and episode:
                lookfor = 8  # tv only

            url = '{}/rss.xml?type=search&cid={}&search=%s'.format(try_url, lookfor)
            full_url = url % encoded_search
            self.url = full_url

            parsed = feedparser.parse(full_url)
            if 'bozo_exception' in parsed:
                continue

            if len(parsed['entries']) == 0:
                continue

            for show in parsed['entries']:
                try:
                    dt = datetime.fromtimestamp(mktime(show['published_parsed']))
                    date = dt.strftime('%b %d/%Y')
                    size = U.pretty_filesize (show['size'])
                    title = show['title']
                except KeyError as e:
                    continue

                # extratorrent returns results that match any word in the
                # search, so the results end up with a bunch of stuff we aren't
                # interested in and we need to filter them out.
                stop = False
                for i in search_string.split(' '):
                    if i.lower() not in title.lower():
                        stop = True
                if stop:
                    continue

                # the ExtraTorrent rss feed doesn't supply the magnet link, or any
                # usable links (They must be downloaded from the site).  But the
                # feed has the URN hash, so we can build a magnet link from that.
                magnet_url = 'magnet:?xt=urn:btih:{}&dn={}'
                magnet_hash = show['info_hash']
                magnet = magnet_url.format(magnet_hash, urllib.parse.quote(title))
                seeds = show['seeders']
                if seeds == '---':
                    seeds = '0'

                show_data.append([
                    title,
                    size,
                    date,
                    seeds,
                    self.shortname,
                    magnet,
                ])

            return show_data

        return show_data

    def download (self, chosen_show, destination, final_name):
        pass


if __name__ == '__main__':

    show = Provider()
    #results = show.search ('"doctor who (2005) 5x01" OR "doctor who 2005 s05e01"')
    #results = show.search ('"doctor who (2005) s05e01"')
    #results = show.search('drunk history s03e04')
    results = show.search('suits')
    pp(results)
