
import urllib.request, urllib.parse, urllib.error
from bs4 import BeautifulSoup
import requests
from pprint import pprint as pp
import click

import concurrent.futures
import socket
from tvoverlord.config import Config


class Provider():

    name = '1337X'
    shortname = '13'  # can only be 2 characters long
    provider_urls = ['http://1337x.to']
    base_url = provider_urls[0]

    def search(self, search_string, season=False, episode=False):

        if season and episode:
            searches = self.se_ep(search_string, season, episode)
        else:
            searches = [search_string]

        search_data = []
        for search in searches:
            search_tpl = '{}/sort-search/{}/seeders/desc/1/'
            search_string = urllib.parse.quote(search)
            url = search_tpl.format(self.base_url, search_string)
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
            search_results = soup.find('tbody')
            if search_results == None:
                continue

            # old soup methods:
            # search_results = soup.find('div', class_='tab-detail')
            # for li in search_results.find_all('li'):
            #    divs = li.find_all('div')
            #    try:
            #        detail_url = divs[0].strong.a['href']
            #        title = divs[0].get_text(strip=True)
            #        seeds = divs[1].get_text(strip=True)
            #        size = divs[3].get_text(strip=True)
            #    except IndexError:
            #        continue

            for tr in search_results:
                if len(tr) == 1:
                    continue

                tds = tr.find_all('td')

                try:
                    detail_url = tds[0].find_all('a')[1]['href']
                    title = tds[0].get_text(strip=True)
                    seeds = tds[1].get_text(strip=True)
                    size = tds[4].contents[0]
                except IndexError:
                    continue

                search_data.append([detail_url, title, seeds, size])

        show_data = []

        # extract the date and magnet from the detail page

        ## ASYNCHRONOUS
        # socket.setdefaulttimeout(3.05)
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            res = {
                executor.submit(self._get_details, detail_data): detail_data for detail_data in search_data
            }
            for future in concurrent.futures.as_completed(res):
                results = future.result()
                show_data.append(results)

        ### SYNCHRONOUS
        #for detail in search_data:
        #    show_data.append(self._get_details(detail))

        return show_data

    def _get_details(self, detail):

        url = '{}{}'.format('http://1337x.to', detail[0])
        try:
            r = requests.get(url, timeout=Config.timeout)
        except requests.exceptions.ConnectionError:
            # can't connect, go to next url
            return

        html = r.content
        soup = BeautifulSoup(html, 'html.parser')

        ## old soup methods:
        # section = soup.find('div', class_='category-detail')
        # magnet = section.find_all('a')[1]['href']
        # date = section.find_all('span')[7].get_text(strip=True)

        section = soup.find('div', class_='torrent-category-detail')
        magnet = section.find_all('a')[0]['href']

        daterow = list(section.find_all('strong')[7].parent.stripped_strings)
        date = daterow[1]

        data = [detail[1], detail[3], date, detail[2], self.shortname, magnet]
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

        return [search_one, search_two]


if __name__ == '__main__':

    p = Provider()
    # results = p.search('game of thrones')
    results = p.search('game of thrones', season=6, episode=6)
    # results = p.search('luther', season=1, episode=5)
    # results = p.search('adf asdf asdf asdf asdf asdf asd f', season=1, episode=5)
    # time: 0:04.74
    # print(results)
    print('>>>len', len(results))
