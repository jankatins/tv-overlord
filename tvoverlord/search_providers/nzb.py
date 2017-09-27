import requests
import xml.etree.ElementTree as etree
import urllib
from pprint import pprint as pp
import datetime
import os
import math
import sys

import click
from tvoverlord.config import Config
from tvoverlord.util import U
import tvoverlord.tvutil as tvu


class Provider:
    def __init__(self, site):
        self.name = site['longname']
        self.shortname = site['shortname']
        self.url = site['url']
        self.apikey = site['apikey']

    def search(self, search_string, season=False, episode=False, idx=None):

        search_string = '%s %s' % (
            search_string.strip(), tvu.sxxexx(season, episode))

        xml_fragment = self.retrieve_data(search_string, season, episode)

        if xml_fragment:
            data = self.format_data(xml_fragment, idx)
        else:
            data = []

        return data

    def retrieve_data(self, search_string, season, episode):
        qs = {
            't':      'search',
            'apikey': self.apikey,
            'q':      search_string,
            'limit':  Config.nzbcount,
            'o':      'xml',
        }
        url = '%s/api?%s' % (self.url, urllib.parse.urlencode(qs))
        self.log('URL', url)

        # retrieve the data with requests
        try:
            r = requests.get(url, timeout=Config.timeout)
            r.raise_for_status()
        except requests.exceptions.InvalidURL as e:
            self.log('InvalidURL', e)
            self.notify('The url in invalid.', e)
            return
        except requests.exceptions.ConnectionError as e:
            self.log('ConnectionError', e)
            self.notify('Connection Error.', e)
            return
        except requests.exceptions.HTTPError as e:
            self.log(e)
            self.notify(e)
            return
        except requests.exceptions.Timeout as e:
            self.log(e)
            self.notify(e)
            return

        if not r.content:
            msg = 'No data return from server'
            self.log(msg)
            self.notify(msg)
            return

        try:
            xmldoc = etree.fromstring(r.content)
        except etree.ParseError as e:
            self.notify(e)
            self.log(e)
            return

        # an error has been returned from newznab
        if xmldoc.tag == 'error':
            msg_content = dict(xmldoc.items())
            error_code = msg_content['code']
            error_desc = msg_content['description']
            if error_code == 100:
                # Incorrect user credentials
                self.log(error_code, error_desc)
                self.notify('Incorrect user credentials.', error_desc)
            elif error_code == 101:
                # Account suspended
                self.log(error_code, error_desc)
                self.notify('Account has been suspended.', error_desc)
            elif error_code == 102:
                # Insufficient privileges/not authorized
                self.log(error_code, error_desc)
                self.notify('Insufficient privileges/not authorized.', error_desc)
            elif error_code == 500:
                # api limit reached
                self.log(error_code, error_desc)
                self.notify('API limit reached.', error_desc)
            else:
                # all other errors
                self.log(error_code, error_desc)
                self.notify(error_desc)

        elif xmldoc.tag == 'rss':
            results = xmldoc.findall('./channel/item')
            return results

        else:
            self.log('Not an xml document')

    def format_data(self, xml_fragment, idx):
        show_data = []
        for show in xml_fragment:
            title = show.find('title').text
            date = show.find('pubDate').text
            date = datetime.datetime.strptime(date, '%a, %d %b %Y %X %z')
            date = date.strftime('%b %d/%Y')

            size = guid = None
            # extract the elements that look like:
            # <newznab:attr name="XXXX" value="XXXX">
            attrs = [dict(i.items()) for i in show if 'name' in i.keys()]
            for attr in attrs:
                if attr['name'] == 'size':
                    size = attr['value']
                    size = U.pretty_filesize(size)
                if attr['name'] == 'guid':
                    guid = attr['value']

            # the guid is sometimes not in a <newznab:attr.../> tag
            if not guid:
                guid = show.find('guid')
                guid = guid.text.split('/')[-1]

            show_data.append([
                title,
                size,
                date,
                self.shortname,
                '%s|%s' % (idx, guid),
            ])
        return show_data

    def log(self, *msg):
        msg = ', '.join([str(i) for i in msg])
        msg = '[site:%s], %s' % (self.name, msg)
        # print(msg)
        Config.logging.info(msg)

    def notify(self, *msg):
        msg = ', '.join([str(i) for i in msg])
        base_pad = (math.ceil(len(msg) / Config.console_columns)
                    * Config.console_columns)
        padding = ' ' * (base_pad - (len(msg) + len(self.name) + 2))
        msg = tvu.style(msg, fg='green')
        sitename = tvu.style(self.name, fg='yellow')
        fullmsg = '%s: %s%s' % (sitename, msg, padding)

        click.echo('%s' % fullmsg, err=True)

    def download(self, chosen_show, destination, final_name):
        if not os.path.isdir(destination):
            click.echo('\n%s does not exist' % destination, err=True)
            sys.exit(1)

        qs = {
            't': 'get',
            'apikey': self.apikey,
            'id': chosen_show,
        }
        url = '%s/api?%s' % (self.url, urllib.parse.urlencode(qs))
        self.log(chosen_show, destination, final_name)
        self.log('GET URL', url)

        fullname = os.path.join(destination, final_name)

        r = requests.get(url, stream=True)
        with open(fullname, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                f.write(chunk)

        return final_name
