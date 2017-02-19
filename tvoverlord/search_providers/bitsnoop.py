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

    provider_urls = [
        'http://bitsnoop.com',            # do not add a trailing slash for bitsnoop
    ]                                     # it causes the search to fail
    name = 'BitSnoop'
    shortname = 'BS'
    url = ''

    @staticmethod
    def se_ep (season, episode, show_title):
        season_just = str (season).rjust (2, '0')
        episode = str (episode).rjust (2, '0')
        #fixed = '"%s S%sE%s" OR "%s %sx%s"' % (
            #show_title, season_just, episode, show_title, season, episode)
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
            url = '%s/search/all/{}/c/d/1/?fmt=rss' % (try_url)
            full_url = url.format(encoded_search)
            self.url = full_url
            #click.echo('>', full_url)

            parsed = feedparser.parse(full_url)
            if len(parsed['entries']) == 0:
                continue

            for show in parsed['entries']:
                if show['published_parsed']:
                    dt = datetime.fromtimestamp(mktime(show['published_parsed']))
                    date = dt.strftime('%b %d/%Y')
                else:
                    date = '-'
                size = U.pretty_filesize (show['size'])
                title = show['title']
                seeds = show['numseeders']
                magnet = show['magneturi']

                show_data.append([
                    title,
                    size,
                    date,
                    seeds,
                    self.shortname,
                    magnet
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
    results = show.search('Gotham S02E01')
    pp(results)

