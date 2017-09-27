import sys
import subprocess
import os
import platform
import concurrent.futures
from pprint import pprint as pp
import socket
import urllib
import click

from tvoverlord.config import Config
from tvoverlord.util import U
import tvoverlord.tvutil as tu

from tvoverlord.search_providers import *


class SearchError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class Search(object):
    def __init__(self):
        self.season = ''
        self.episode = ''
        self.show_name = ''
        self.se_order = []

        torrent_engines = [
            bitsnoop, extratorrent, thepiratebay_sx, btstorr_cc,
            onethreethreesevenx_to, rarbg_to, eztv_ag]

        newsgroup_engines = [nzbclub_com.Provider()]

        # remove any providers listed in the blacklist
        self.torrent_engines = []
        for engine in torrent_engines:
            inlist = True
            if engine.Provider.shortname.lower() in Config.blacklist:
                inlist = False
            if engine.Provider.name.lower() in Config.blacklist:
                inlist = False
            if inlist:
                self.torrent_engines.append(engine.Provider())

        self.newsgroup_engines = []
        for engine in newsgroup_engines:
            inlist = True
            if engine.shortname.lower() in Config.blacklist:
                inlist = False
            if engine.name.lower() in Config.blacklist:
                inlist = False
            if inlist:
                self.newsgroup_engines.append(engine)

        for site in Config.nzbs:
            self.newsgroup_engines.append(
                nzb.Provider(site))

    def job(self, engine, search_string, season, episode, date_search, idx=None):
        search = engine
        if date_search:
            search_string = '%s %s' % (search_string, date_search)
            season = episode = False

        if self.search_type == 'torrent':
            search_results = search.search(search_string, season, episode)
        elif self.search_type == 'nzb':
            search_results = search.search(search_string, season, episode, idx)

        self.se_order.append(search.name)
        return search_results + [search.name]

    def test_each(self, search_string, show_results):
        """Do a test search for each search engine"""
        engines = self.torrent_engines + self.newsgroup_engines
        indent = '  '
        click.echo()
        click.echo('Searching for: %s' % search_string)
        for engine in engines:
            search = engine
            name = '%s (%s)' % (search.name, search.shortname)
            click.echo(tu.style(name, bold=True))

            results = search.search(search_string)

            click.echo(indent + tu.style(search.url, fg='blue', ul=True))
            results_count = str(len(results))
            if results_count == '0':
                results_count = tu.style(results_count, fg='red')
            else:
                results_count = tu.style(results_count, fg='green')
            click.echo(indent + 'Search results: %s' % results_count)

            if show_results:
                for result in results:
                    click.echo('%s* %s' % (indent, result[0]))

    def search(self, search_string, season=False, episode=False,
               date_search=None, search_type='torrent'):
        """
        Return an array of values:

        [
          [
            ['Title string', 'search url'],
            [head1, head2, head3, id],
            [head1-width, head2-width, head3-width],
            [head1-alignment, head2-alignment, head3-alignment]
          ],
          [
            [<column 1 data>, <column 2 data>, <column 3 data>, <id>],
            [<column 1 data>, <column 2 data>, <column 3 data>, <id>],
            # etc...
          ]
        ]
        """

        self.season = season
        self.episode = episode
        self.show_name = search_string
        self.search_type = search_type

        click.echo()

        if self.search_type == 'torrent':
            header = [
                [search_string, ''],
                ['Name', 'Size', 'Date', 'Seeds', 'SE'],
                [0, 10, 12, 6, 2],
                ['<', '>', '<', '>', '<']]
        else:
            header = [
                [search_string, ''],
                ['Name', 'Size', 'Date', 'SE'],
                [0, 10, 12, 3],
                ['<', '>', '<', '<']]

        if self.search_type == 'torrent':
            engines = self.torrent_engines
        elif self.search_type == 'nzb':
            engines = self.newsgroup_engines
        else:
            raise ValueError('search_type can only be "torrent" or "nzb"')

        socket.setdefaulttimeout(Config.timeout)
        episodes = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            # For nzb's, the idx is needed so Provider.download knows
            # which engine was used.  It's not needed for torrents
            # because there is no download method.
            res = {
                executor.submit(
                    self.job, engine, search_string, season, episode, date_search, idx
                ): engine for idx, engine in enumerate(engines)
            }

            names = [i.name for i in engines]
            names.sort()
            names = [' %s ' % i for i in names]
            names = [tu.style(i, fg='white', bg='red') for i in names]
            for future in concurrent.futures.as_completed(res):

                results = future.result()
                finished_name = results[-1]
                for i, e in enumerate(names):
                    e = click.unstyle(e).strip()
                    if e == finished_name:
                        e = ' %s ' % e
                        names[i] = tu.style(e, fg='white', bg='green')

                if date_search:
                    title = '%s %s' % (search_string.strip(),
                                       date_search)
                else:
                    title = '%s %s' % (search_string.strip(),
                                       tu.sxxexx(season, episode))
                title = title.ljust(Config.console_columns)
                click.echo(tu.style(title, bold=True))
                click.echo(' '.join(names))
                # move up two lines
                click.echo('[%sA' % 3)

                if self.search_type == 'torrent':
                    episodes = episodes + results[:-1]
                elif self.search_type == 'nzb':
                    # episodes = episodes + results[:-1]
                    if episodes:
                        episodes.append(results[:-1])

        # go up 3 lines to remove the progress bar
        click.echo('[%sA' % 2)

        if self.search_type == 'torrent':
            self.sort_torrents(episodes)
        else:
            pp(episodes)
            exit()

        if Config.filter_list:
            episodes = [i for i in episodes if self.filter_episode(i)]

        self.episodes = episodes
        # return search_results
        return [header] + [episodes]

    def filter_episode(self, episode):
        bad = False
        for f in Config.filter_list:
            if f.lower() in episode[0].lower():
                bad = True
        if not bad:
            return episode

    def sort_torrents(self, episodes):
        # sort by seeds
        episodes.sort(key=lambda x: int(x[3]), reverse=True)

        # Remove torrents with 0 seeds
        for i, episode in enumerate(episodes):
            seeds = int(episode[3])
            # click.echo(episode[0])
            if not seeds:
                # click.echo('    %s %s' % (seeds, episode[0]))
                del episodes[i]

        # remove duplicates since different sites might
        # have the same torrent
        titles = []
        for i, episode in enumerate(episodes):
            title = episode[0]
            if title in titles:
                del episodes[i]
            else:
                titles.append(title)

        # remove duplicates based on the magnet hash
        hashes = []
        for i, episode in enumerate(episodes):
            o = urllib.parse.urlparse(episode[5])
            torrent_hash = urllib.parse.parse_qs(o.query)['xt']
            torrent_hash = torrent_hash[0].split(':')[-1]
            if torrent_hash in hashes:
                del episodes[i]
            else:
                hashes.append(torrent_hash)

    def magnet_filename(self, chosen_show=None):
        se_ep = tu.sxxexx(self.season, self.episode)
        if se_ep:
            fullname = '%s %s.magnet' % (self.show_name, se_ep)
            fullname = fullname.replace(' ', '_')
        else:
            show_fname = self.show_name
            for f in self.episodes:
                if chosen_show == f[5]:
                    show_fname = tu.clean_filename(f[0], strict=True)
            fullname = '%s.magnet' % (show_fname)
        return fullname

    def config_command(self, chosen_show):
        args = [i.replace('{magnet}', chosen_show) for i in Config.client]
        if args == Config.client:
            sys.exit('\nNo {magnet} replacement flag was found in config.ini, client section.')

        return args

    def download(self, chosen_show, destination, search_type='torrent'):
        """
        Pass the chosen show's data and destination to the providers
        download method and return the name of the file downloaded
        back to get-nzb.v2.py
        """
        downloaded_filename = ''
        if chosen_show.startswith("magnet:"):

            # write magnet links to a file
            if Config.magnet_dir:
                Config.magnet_dir = os.path.expanduser(Config.magnet_dir)
                fn = self.magnet_filename(chosen_show)
                if os.path.isdir(Config.magnet_dir):
                    full = os.path.join(Config.magnet_dir, fn)
                    with open(full, 'w') as f:
                        f.write(chosen_show)
                else:
                    sys.exit('\n"%s" does not exist' % Config.magnet_dir)

            # use a command specified in config.ini
            elif Config.client:
                args = self.config_command(chosen_show)
                try:
                    subprocess.Popen(args)
                except FileNotFoundError:
                    sys.exit('\n"%s" not found.' % args[0])

            elif platform.system() == 'Linux':
                err_msg = tu.format_paragraphs('''
                    You do not have a default handler for magnet
                    links.  Either install a bittorent client or
                    configure the "magnet folder" or "client"
                    settings in config.ini.''')

                isX = True if os.environ.get('DISPLAY') else False
                if isX:
                    app = 'xdg-open'
                else:
                    click.echo()
                    sys.exit(err_msg)

                try:
                    subprocess.Popen([app, chosen_show],
                                     stderr=subprocess.DEVNULL,
                                     stdout=subprocess.DEVNULL)
                except OSError:
                    click.echo()
                    sys.exit(err_msg)

            elif platform.system() == 'Darwin':
                subprocess.Popen(["open", "--background", chosen_show])

            elif platform.system() == 'Windows':
                os.startfile(chosen_show)

            else:
                unknown_system = platform.platform()
                sys.exit('\nUnknown system:', unknown_system)

        else:  # is a nzb file
            final_name = ''

            show_fname = 'unknown'
            for f in self.episodes:
                if chosen_show == f[4]:
                    show_fname = tu.clean_filename(f[0], strict=True)
            final_name = '%s.nzb' % (show_fname)

            idx, guid = chosen_show.split('|')
            downloader = self.newsgroup_engines[int(idx)]
            downloaded_filename = downloader.download(
                guid, destination, final_name)

        return downloaded_filename

    def progress_title(self, future):
        """Display the search engine name on the right side of the progressbar"""
        try:
            engine_name = future.result()[-1]
            engine_name += ' done'
            self.last_engine = engine_name
            return engine_name
        except AttributeError:
            engine_name = ''
            return


if __name__ == '__main__':
    test = Search('nzbindex')
    test = Search('NZBIndex')
    test = Search('x')
