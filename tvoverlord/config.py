import os
import sys
import platform
import configparser
import shutil
import sqlite3
import click
import shlex
import pathlib
import logging
import logging.handlers
from types import SimpleNamespace as SN
from pprint import pprint as pp


def message(msg, filename):
    click.secho(msg, bold=True)
    click.secho('  %s' % filename, fg='green')
    return True


class ConfigFileBuilder:
    is_win = True if platform.system() == 'Windows' else True

    def __init__(self, dir_name, app_config_name):
        self.dir_name = dir_name
        self.user_home = None
        self.user_config = None
        self.app_config_name = app_config_name
        self.app_config = None
        self.user_db = None
        self.oldfields = None

    def create_config_dir(self):
        """Create the config dir

        Create it in the default location for the users platform and
        only if it doesn't already exist.
        """
        dir_path = click.get_app_dir(self.dir_name)
        dir_path = pathlib.Path(dir_path)
        self.user_home = dir_path
        if not dir_path.exists():
            dir_path.mkdir(parents=True)
            return True
        else:
            return False

    def create_config(self, config_name):
        """Ensure that the config file exists

        :param config_name: Name of config file
        """
        self.user_config = self.user_home / config_name

        app_home = pathlib.Path(__file__).parent
        self.app_config = app_home / self.app_config_name

        if not self.user_config.exists():
            self.write_config()
            # shutil.copy(str(self.app_config), str(self.user_home))
            return True
        else:
            return False

    def write_config(self):
        # this will write the text file with the correct line endings
        # for the platform
        with self.app_config.open() as source, \
             self.user_config.open('w') as dest:
            for line in source:
                dest.write(line)

    def create_modify_db(self, db_name, sqldata):
        """Create the DB is it doesn't exist"""

        self.user_db = self.user_home / db_name
        if not self.user_db.exists():
            sql = self.generate_tables(sqldata)
            self.new_db(sql)
            return True
        else:
            modified = False
            for table in sqldata:
                if self.table_changed(table):
                    self.update_db(table)
                    modified = True
            return modified

    def generate_table(self, table):
        sql = ['CREATE TABLE %s (' % table['name']]
        fieldsa = []
        for field in table['fields']:
            fieldsa.append('    %s %s' % (field[0], field[1]))
        fields = ',\n'.join(fieldsa)
        sql.append(fields)
        try:
            extra = ', %s' % table['extra']
            sql.append(extra)
        except KeyError:
            pass
        sql.append(');')
        sql = '\n'.join(sql)
        return sql

    def generate_tables(self, sqldata):
        tables = []
        for table in sqldata:
            tables.append(self.generate_table(table))
        sql = '\n'.join(tables)
        return sql

    def table_changed(self, table):
        conn = sqlite3.connect(str(self.user_db))
        sql = 'SELECT * from %s;' % table['name']

        try:
            curs = conn.execute(sql)
        except sqlite3.OperationalError:
            # the db exists, but this particular table doesn't exist
            # yet.
            newsql = self.generate_table(table)
            self.new_db(newsql)
        finally:
            curs = conn.execute(sql)
        self.oldfields = {f[0] for f in curs.description}
        newfields = {f[0] for f in table['fields']}
        return self.oldfields != newfields

    def update_db(self, table):
        backupname = 'backup_%s' % table['name']

        backupsql = 'ALTER TABLE %s RENAME TO %s;' % (
            table['name'], backupname)
        newtable = self.generate_table(table)
        fieldnames = ',\n'.join(self.oldfields)
        copydata = 'INSERT INTO %s (%s) SELECT %s FROM %s;' % (
            table['name'], fieldnames, fieldnames, backupname)
        delbackup = 'DROP TABLE %s;' % backupname

        conn = sqlite3.connect(str(self.user_db))
        conn.isolation_level = None
        curs = conn.cursor()
        try:
            curs.execute('BEGIN')
            curs.execute(backupsql)
            curs.execute(newtable)
            curs.execute(copydata)
            curs.execute(delbackup)
            curs.execute('COMMIT')
        except conn.Error as e:
            click.echo('Database update failed', err=True)
            click.echo(', '.join(e.args), err=True)
            curs.execute('ROLLBACK')
            sys.exit(1)

    def new_db(self, sql):
        conn = sqlite3.connect(str(self.user_db))
        conn.executescript(sql)
        conn.commit()
        conn.close()


class Configuration:
    def __init__(self):
        self.is_win = False
        if platform.system() == 'Windows':
            self.is_win = True

        self.thetvdb_apikey = 'DFDB0A667C844513'
        self.use_cache = True

        console_columns, console_rows = click.get_terminal_size()
        self.console_columns = int(console_columns)
        if self.is_win:
            # On windows, columns are 1 char too wide
            console_columns = console_columns - 1

        # progressbar settings
        pb = SN()
        pb.width = 50
        if console_columns < 90:
            pb.width = 30
        if console_columns < 80:
            pb.width = 20
        if self.is_win:
            pb.light = 'green'
            pb.dark = 'blue'
        else:
            pb.light = 35
            pb.dark = 23
        pb.empty_char = ' '
        pb.fill_char = '*'
        pb.template = '%(label)s %(bar)s %(info)s'
        self.pb = pb

        if self.is_win:
            color = SN()
            color.table = SN(
                title=SN(fg='white', bg='green'),
                header=SN(fg='white', bg='blue'),
                body=SN(fg='white', bg=None),
                bar=SN(fg='green', bg=None),
                hidef=SN(fg='green', bg=None),
            )
            color.info = SN(
                links=SN(fg='blue', bg=None),
                ended=SN(fg='red', bg=None),
                last=SN(fg='cyan', bg=None),
                future=SN(fg='green', bg=None),
            )
            color.calendar = SN(
                header=SN(fg='white', bg='blue'),
                dates=SN(fg='white', bg=None),
                titles=SN(fg='white', bg=None),
                altdates=SN(fg='white', bg='blue'),
                alttitles=SN(fg='white', bg='blue'),
            )
            color.missing = SN(fg='green', bg=None)
            color.edit = SN(fg='yellow', bg='black')
            color.warn = SN(fg='yellow', bg='black')
        else:
            color = SN()
            color.table = SN(
                title=SN(fg=None, bg=19),
                header=SN(fg=None, bg=17),
                body=SN(fg='white', bg=None),
                bar=SN(fg=19, bg=None),
                hidef=SN(fg=76, bg=None),
            )
            color.info = SN(
                links=SN(fg=20, bg=None),
                ended=SN(fg='red', bg=None),
                last=SN(fg=48, bg=None),
                future=SN(fg=22, bg=None),
            )
            color.calendar = SN(
                header=SN(fg='white', bg=17),
                dates=SN(fg='white', bg=None),
                titles=SN(fg='white', bg=None),
                altdates=SN(fg='white', bg=17),
                alttitles=SN(fg='white', bg=18),
            )
            color.missing = SN(fg='green', bg=None)
            color.edit = SN(fg='yellow', bg='black')
            color.warn = SN(fg='yellow', bg='black')

        self.color = color

        # number of ip address octets to match to be considered ok.  Must
        # be between 1 and 4
        self.parts_to_match = 3

    def create_config(self, config_name, create=False):
        files_created = False
        user_config_dir = 'tvoverlord'
        app_config_name = 'config.ini'
        cb = ConfigFileBuilder(user_config_dir, app_config_name)
        self.cb = cb

        if cb.create_config_dir():
            files_created = message('App config dir created:', cb.user_home)

        if cb.user_home:
            log_file = str(cb.user_home / 'tvol.log')
            f = logging.Formatter(
                fmt='%(asctime)s: %(levelname)s %(filename)s:%(lineno)d: %(message)s',
                datefmt="%Y-%m-%d %H:%M:%S")

            handler = logging.handlers.RotatingFileHandler(
                log_file, maxBytes=500000, backupCount=1)

            root_logger = logging.getLogger()
            root_logger.setLevel(logging.DEBUG)
            handler.setFormatter(f)
            handler.setLevel(logging.DEBUG)
            root_logger.addHandler(handler)

            self.logging = root_logger

        if config_name and create is False:
            config_file = 'config.%s.ini' % config_name
            db_file = 'shows.%s.sqlite3' % config_name
            config_home = click.get_app_dir(user_config_dir)

            if not os.path.exists(os.path.join(config_home, config_file)):
                msg = 'Warning: %s does not exist, using config.ini' % config_file
                click.secho(msg, fg='yellow', err=True)
                config_file = 'config.ini'

            if not os.path.exists(os.path.join(config_home, db_file)):
                msg = 'Warning: %s does not exist, using shows.sqlite3' % db_file
                click.secho(msg, fg='yellow', err=True)
                db_file = 'shows.sqlite3'

        elif config_name and create is True:
            config_file = 'config.%s.ini' % config_name
            db_file = 'shows.%s.sqlite3' % config_name

        else:
            config_file = 'config.ini'
            db_file = 'shows.sqlite3'

        if cb.create_config(config_file):
            files_created = message(
                '%s created:' % cb.user_config.name, cb.user_config)

        self.user_config = str(cb.user_config)
        self.user_dir = str(cb.user_home)

        sql = [
            {
                'name': 'shows',
                'fields': [
                    ['id', 'INTEGER PRIMARY KEY AUTOINCREMENT'],
                    ['name', 'TEXT'],
                    ['search_engine_name', 'TEXT'],
                    ['display_name', 'TEXT'],
                    ['date_added', 'TEXT'],
                    ['network_status', 'TEXT'],
                    ['status', 'TEXT'],
                    ['thetvdb_series_id', 'TEXT'],
                    ['ragetv_series_id', 'TEXT'],
                    ['imdb_series_id', 'TEXT'],
                    ['alt_series_id', 'TEXT'],
                    ['season', 'NUMERIC'],
                    ['episode', 'NUMERIC'],
                    ['search_by_date', 'INTEGER'],
                    ['date_format', 'TEXT'],
                    ['next_episode', 'TEXT'],
                    ['airs_time', 'TEXT'],
                    ['airs_dayofweek', 'TEXT'],
                    ['rating', 'TEXT'],
                    ['auto_download', 'TEXT'],
                    ['notes', 'TEXT'],
                ],
            },
            {
                'name': 'tracking',
                'fields': [
                    ['download_date', 'TEXT'],
                    ['show_title', 'TEXT'],
                    ['season', 'TEXT'],
                    ['episode', 'TEXT'],
                    ['download_data', 'TEXT'],
                    ['chosen', 'TEXT'],
                    ['chosen_hash', 'TEXT'],
                    ['one_off', 'INTERGER'],
                    ['complete', 'INTERGER'],
                    ['filename', 'TEXT'],
                    ['destination', 'TEXT'],
                ]
            },
            {
                'name': 'settings',
                'extra': 'UNIQUE(key)',
                'fields': [
                    ['id', 'INTEGER PRIMARY KEY AUTOINCREMENT'],
                    ['key', 'TEXT'],
                    ['value', 'TEXT'],
                ]
            }
        ]
        if cb.create_modify_db(db_file, sql):
            files_created = message(
                'Database has been created/updated:', cb.user_db)

        if files_created:
            click.echo('-' * self.console_columns)
            click.echo()

        self.db_file = str(cb.user_db)

    def get_config_data(self, config_name=None):
        self.create_config(config_name)

        categories = SN()
        categories.resolution = [
            '1080p', '1080i', '720p', '720i', 'hr', '576p',
            '480p', '368p', '360p']
        categories.sources = [
            'bluray', 'remux', 'dvdrip', 'webdl', 'hdtv', 'bdscr',
            'dvdscr', 'sdtv', 'webrip', 'dsr', 'tvrip', 'preair',
            'ppvrip', 'hdrip', 'r5', 'tc', 'ts', 'cam', 'workprint']
        categories.codecs = [
            '10bit', 'h265', 'h264', 'x264', 'xvid', 'divx']
        categories.audio = [
            'truehd', 'dts', 'dtshd', 'flac', 'ac3', 'dd5.1', 'aac', 'mp3']

        self.categories = categories

        cfg = configparser.ConfigParser(
            allow_no_value=True, interpolation=None)
        try:
            cfg.read(str(self.cb.user_config))
        except configparser.DuplicateSectionError as e:
            click.echo(e, err=True)
            click.echo('Section names in config file must all be unique.', err=True)
            sys.exit(1)

        # Settings from config.ini ---------------------------------
        try:
            self.warnvpn = True if cfg.get(
                'App Settings', 'warn vpn') == 'yes' else False
        except configparser.NoOptionError:
            self.warnvpn = False

        try:
            self.email = cfg.get('App Settings', 'email')
        except configparser.NoOptionError:
            self.email = False

        try:
            self.single_file = True if cfg.get(
                'App Settings', 'single file') == 'yes' else False
        except configparser.NoOptionError:
            self.single_file = False

        try:
            self.template = cfg.get('App Settings', 'template')
        except configparser.NoOptionError:
            self.template = False

        try:
            self.search_type = 'nzb' if cfg.get(
                'App Settings', 'search type') == 'nzb' else 'torrent'
        except configparser.NoOptionError:
            self.search_type = 'torrent'

        try:
            client = cfg.get('App Settings', 'client')
            self.client = shlex.split(client)
        except configparser.NoOptionError:
            self.client = None

        try:
            self.magnet_dir = cfg.get('App Settings', 'magnet folder')
        except configparser.NoOptionError:
            self.magnet_dir = None

        try:
            blacklist = cfg.get('App Settings', 'blacklist')
            # split, strip, and remove empty values from list
            self.blacklist = [
                i.strip().lower() for i in blacklist.split(',') if i.strip()]
        except configparser.NoOptionError:
            self.blacklist = []

        try:
            self.version_notification = False if cfg.get(
                'App Settings', 'version notification') == 'no' else True
        except configparser.NoOptionError:
            self.version_notification = True

        # collecting telemetry data is not ok only if the user has set
        # 'telemetry: no'
        try:
            self.telemetry_ok = False if (
                cfg.get('App Settings', 'telemetry') == 'no') else True
        except configparser.NoOptionError:
            self.telemetry_ok = None

        try:
            filter_list = cfg.get('App Settings', 'filters')
            self.filter_list = [
                i.strip().lower() for i in filter_list.split(',') if i.strip()]
        except configparser.NoOptionError:
            self.filter_list = []

        default_timeout = 10
        try:
            self.timeout = float(cfg.get('App Settings', 'timeout'))
        except configparser.NoOptionError:
            self.timeout = default_timeout
        if not self.timeout:
            self.timeout = default_timeout

        # [File Locations]
        try:
            self.tv_dir = os.path.expanduser(
                cfg.get('File Locations', 'tv dir'))
        except configparser.NoOptionError:
            self.tv_dir = None
        try:
            self.staging = os.path.expanduser(
                cfg.get('File Locations', 'staging'))
        except configparser.NoOptionError:
            self.staging = None

        # [Newznab]
        try:
            newznab = dict(cfg['Newznab'])
            self.newznab = {
                k: [i.strip() for i in v.split(',')]
                for k, v in newznab.items()}
        except KeyError:
            self.newznab = {}

        # [nzb]
        self.nzbs = [
            dict(v) for k, v in cfg.items() if k.lower().startswith('nzb:')]


Config = Configuration()


if __name__ == '__main__':
    c = Config()
    click.echo(c.staging)
    pass
