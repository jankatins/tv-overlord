import urllib.request, urllib.parse, urllib.error
import requests
from pprint import pprint as pp
import time
import click
from tvoverlord.util import U
from tvoverlord.config import Config


# https://torrentapi.org/apidocs_v2.txt

class Provider():

    name = 'RARBG'
    shortname = 'RB'
    provider_urls = ['https://torrentapi.org/pubapi_v2.php']
    baseurl = provider_urls[0]
    url = ''

    def search(self, search_string, season=False, episode=False):

        if season and episode:
            searches = self.se_ep(search_string, season, episode)
        else:
            searches = [search_string]

        # get token for api
        url = '{}?get_token=get_token&app_id=tvoverlord'.format(self.baseurl)

        try:
            r = requests.get(url, timeout=Config.timeout)
        except requests.exceptions.ConnectionError:
            return []
        except requests.exceptions.Timeout:
            return []

        if r.status_code == 403:
            self.url = url
            return []

        try:
            j = r.json()
        except ValueError:
            return []  # not json

        token = j['token']

        search_data = []
        count = 0
        for search in searches:
            # the torrentapi only allows one query every two seconds
            if count > 0:
                time.sleep(2)
            count = count + 1

            search_tpl = '{}?mode=search&search_string={}&token={}&format=json_extended&sort=seeders&limit=100&app_id=tvoverlord'
            search_string = urllib.parse.quote(search)
            url = search_tpl.format(self.baseurl, search_string, token)
            # click.echo(url)
            self.url = self.url + ' ' + url

            try:
                r = requests.get(url, timeout=Config.timeout)
            except requests.exceptions.ConnectionError:
                # can't connect, go to next url
                continue
            except requests.exceptions.Timeout:
                continue

            try:
                results = r.json()
            except:
                continue
            if 'error_code' in results.keys() and results['error_code'] == 20:
                continue  # no results found

            try:
                shows = results['torrent_results']
            except KeyError:
                # no results
                continue

            for show in shows:
                title = show['title']
                date = show['pubdate']
                date = date.split(' ')[0]
                size = show['size']
                size = U.pretty_filesize(size)
                seeds = show['seeders']
                magnet = show['download']

                search_data.append([title, size, date, seeds,
                                    self.shortname, magnet])

        return search_data

    @staticmethod
    def se_ep(show_title, season, episode):
        season = str(season)
        episode = str(episode)
        search_one = '%s S%sE%s' % (
            show_title,
            season.rjust(2, '0'),
            episode.rjust(2, '0'))

        search_two = '%s %sx%s' % (
            show_title,
            season,
            episode.rjust(2, '0'))

        return [search_one, search_two]


if __name__ == '__main__':

    p = Provider()
    # results = p.search('game of thrones')
    # results = p.search('game of thrones', season=6, episode=6)
    # results = p.search('luther', season=1, episode=5)
    results = p.search('shades of blue', season=1, episode=5)
    # results = p.search('adf asdf asdf asdf asdf asd f', season=1, episode=5)
    # click.echo('>>>len', len(results))
    pp(results)
