import urllib.request, urllib.parse, urllib.error
from bs4 import BeautifulSoup
import requests
from pprint import pprint as pp
import concurrent.futures
from tvoverlord.util import U
from tvoverlord.config import Config


class Provider():

    name = 'EZTV'
    shortname = 'EZ'
    provider_urls = ['https://eztv.ag']

    base_url = provider_urls[0]

    def search(self, search_string, season=False, episode=False):

        if season and episode:
            searches = self.se_ep(search_string, season, episode)
        else:
            searches = [search_string]

        search_data = []
        for search in searches:
            search_string = search
            search_tpl = '{}/search/{}'
            search = search.replace(' ', '-')
            search = urllib.parse.quote(search)
            url = search_tpl.format(self.base_url, search)
            self.url = url
            try:
                r = requests.get(url, timeout=Config.timeout)
            except requests.exceptions.ConnectionError:
                # can't connect, go to next url
                continue
            except requests.exceptions.Timeout:
                continue

            html = r.content
            soup = BeautifulSoup(html, 'html.parser')
            search_results = soup.find_all('tr', class_='forum_header_border')
            if search_results is None:
                continue

            for tr in search_results:
                try:
                    tds = tr.find_all('td')
                    title = tds[1].get_text(strip=True)
                    if not self.match(search_string, title):
                        continue
                    detail_url = tds[1].a['href']
                    magnet = tds[2].a['href']
                    if not magnet.startswith('magnet'):
                        continue
                    size = tds[3].get_text(strip=True)
                    date = tds[4].get_text(strip=True)
                except TypeError as e:
                    print(e)
                    continue

                search_data.append([detail_url, title, date, magnet, size])

        show_data = []

        async = True
        if async:
            # ASYNCHRONOUS
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                res = {
                    executor.submit(self._get_details, torrent): torrent for torrent in search_data
                }
                for future in concurrent.futures.as_completed(res):
                    results = future.result()
                    show_data.append(results)

        else:
            # SYNCHRONOUS
            for torrent in search_data:
                show_data.append(self._get_details(torrent))

        return show_data

    def match(self, search_str, title):
        search_str = search_str.casefold()
        search_str = search_str.split()
        title = title.casefold()
        for i in search_str:
            if i == 'the':
                continue
            if i not in title:
                return False
        return True

    def _get_details(self, torrent):
        url = '{}{}'.format(self.base_url, torrent[0])
        try:
            r = requests.get(url, timeout=Config.timeout)
        except requests.exceptions.ConnectionError:
            # can't connect, go to next url
            return

        html = r.content
        soup = BeautifulSoup(html, 'html.parser')
        seeds = soup.find('span', class_='stat_red')#.get_text(strip=True)
        if seeds:
            seeds = seeds.get_text(strip=True)
            seeds = seeds.replace(',', '')
        else:
            seeds = 0
        # date = section.find_all('span')[7].get_text(strip=True)

        # title size date seeds shortname magnet
        data = [torrent[1], torrent[4], torrent[2],
                seeds, self.shortname, torrent[3]]
        return data

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

        # eztv doesn't use the search_two style
        # return [search_one, search_two]
        return [search_one]


if __name__ == '__main__':

    import click
    p = Provider()
    results = p.search('Jonathan strange Norrell')
    # results = p.search('game of thrones', season=6, episode=6)
    # results = p.search('luther', season=1, episode=5)
    pp(results)
    click.echo('>>>len', len(results))
