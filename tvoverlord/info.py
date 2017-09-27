import datetime
from pprint import pprint as pp
from dateutil import parser as date_parser
import click

from tvoverlord.shows import Shows
from tvoverlord.config import Config
from tvoverlord.tvutil import style, format_paragraphs


def info(show_name, show_all, sort_by_next, db_status,
         ask_inactive, show_links, synopsis):
    """Show information about your tv shows.

    SHOW_NAME can be a full or partial name of a show.  If used, it
    will show information about any shows that match that string, else
    it will show informaton about all your shows.
    """
    show_info = {}
    counter = 0
    status = 'active'

    # When the user specifies a single show, turn on --show-all
    # because the show they are asking for might an inactive show
    # and turn on --synopsis and --show-links since its only one
    # show we may as well show everything
    filter_name = ''
    if show_name:
        show_all = True
        synopsis = True
        show_links = True
        filter_name = show_name
        db_status = 'all'

    if Config.is_win:
        colors = {'links': 'blue', 'ended': 'red',
                  'last': 'cyan', 'future': 'green'}
    else:
        colors = {'links': 20, 'ended': 'red',
                  'last': 48, 'future': 22}

    shows = Shows(name_filter=filter_name, status=db_status)
    for show in shows:
        title = show.db_name

        if show.status == 'Ended':
            status = style(show.status, fg=colors['ended'])
        else:
            status = ''

        # build first row of info for each show
        se = 'Last downloaded: S%sE%s' % (
            str(show.db_current_season).rjust(2, '0'),
            str(show.db_last_episode).rjust(2, '0'),
        )
        se = style(se, fg=colors['last'])

        imdb_url = thetvdb_url = ''
        if show_links:
            imdb_url = style('\n    IMDB.com:    http://imdb.com/title/%s' % show.imdbId,
                             fg=colors['links'])
            thetvdb_url = style('\n    TheTVDB.com: http://thetvdb.com/?tab=series&id=%s' % show.id,
                                fg=colors['links'])

        synopsis_text = None
        if synopsis and show.overview:
            paragraph = show.overview
            indent = '    '
            paragraph = format_paragraphs(paragraph, indent=indent)
            synopsis_text = '\n%s' % paragraph

        first_row_a = []
        fancy_title = style(title, bold=True)
        for i in [fancy_title + ',', se, status, imdb_url, thetvdb_url, synopsis_text]:
            if i: first_row_a.append(i)
        first_row = ' '.join(first_row_a)

        # build 'upcoming episodes' list
        today = datetime.datetime.today()
        first_time = True
        episodes_list = []
        counter += 1
        for i in show.series:  # season
            for j in show.series[i]:  # episode
                b_date = show.series[i][j]['firstaired']
                if not b_date: continue  # some episode have no broadcast date?

                split_date = b_date.split('-')
                broadcast_date = datetime.datetime(
                    int(split_date[0]), int(split_date[1]), int(split_date[2]))

                if not show_all:
                    if broadcast_date < today:
                        continue

                future_date = date_parser.parse(b_date)
                diff = future_date - today
                fancy_date = future_date.strftime('%b %d')
                if broadcast_date >= today:
                    episodes_list.append('S%sE%s, %s (%s)' % (
                        show.series[i][j]['seasonnumber'].rjust(2, '0'),
                        show.series[i][j]['episodenumber'].rjust(2, '0'),
                        fancy_date,
                        diff.days + 1,
                    ))

                if first_time:
                    first_time = False
                    if sort_by_next:
                        sort_key = str(diff.days).rjust(5, '0') + str(counter)
                    else:
                        sort_key = show.db_name.replace('The ', '')

        if not first_time:
            if episodes_list:
                indent = '    '
                episode_list = 'Future episodes: ' + ' - '.join(episodes_list)
                episodes = format_paragraphs(episode_list, indent=indent)
                show_info[sort_key] = first_row + '\n' + episodes
            else:
                show_info[sort_key] = first_row

        if ask_inactive:
            if show.status == 'Ended' and first_time:
                click.echo(
                    '%s has ended, and all have been downloaded. Set as inactive? [y/n]: ' %
                    title)
                set_status = click.getchar()
                click.echo(set_status)
                if set_status == 'y':
                    show.set_inactive()

    keys = list(show_info.keys())
    keys.sort()
    full_output = ''
    for i in keys:
        full_output = full_output + show_info[i] + '\n\n'

    # remove the last '\n\n'
    full_output = full_output.strip()

    if len(keys) < 4:
        click.echo(full_output)
    elif Config.is_win:
        click.echo(full_output)
    else:
        click.echo_via_pager(full_output)
