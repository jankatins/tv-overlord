import datetime
from pprint import pprint as pp
import click

from tvoverlord.tvutil import style
from tvoverlord.shows import Shows
from tvoverlord.config import Config


def calendar(show_name, show_all, sort_by_next, no_color, days):
    """Display a calendar of upcoming episodes.

    If SHOW_NAME is used, it will display a calendar for any shows that
    match that string.

    --days can be one number or two numbers.  If one number is used, it will
    show that many days ahead.  If two numbers are used, the first number is
    where the calendar will start and the second number is where it will end.
    The two number must be seperated by a comma with no spaces.

    \b
    --days 10      will show from today to 10 days in the future
    --days 10,20   will start ten days from now and then show 20 days ahead.
    --days -20,10  will go back 20 days from today and then show ahead from there.
    """
    if no_color:
        use_color = False
    else:
        use_color = True

    # set colors for ui elements
    if Config.is_win:
        foreground = 'white'
        header_color = 'blue'
        date_color_1 = 'blue'
        date_color_2 = 0
        title_color_1 = 'blue'
        title_color_2 = 0
    else:
        foreground = 225
        header_color = 17
        date_color_1 = 17
        date_color_2 = 0
        title_color_1 = 18
        title_color_2 = 0

    title_width = 20  # width of show titles column
    spacer = ' '  # can be any string, any length
    today = datetime.datetime.today()

    if days:
        days = days.split(',')
        days = [int(x) for x in days]
        if len(days) == 2:
            today = today + datetime.timedelta(days=days[0])
            calendar_columns = days[1]
        if len(days) == 1:
            calendar_columns = days[0]
    else:
        calendar_columns = Config.console_columns - (title_width + len(spacer))

    # Days_chars can be any string of seven chars. eg: 'mtwtfSS'
    days_chars = '.....::'  # first char is monday
    monthstart = '|'  # marker used to indicate the begining of month

    # build date title row
    months_row = today.strftime('%b') + (' ' * calendar_columns)
    days_row = ''
    daybefore = today - datetime.timedelta(days=1)
    for days in range(calendar_columns):
        cur_date = today + datetime.timedelta(days=days)

        if cur_date.month != daybefore.month:
            days_row += monthstart
            month = cur_date.strftime('%b')
            month_len = len(month)
            months_row = months_row[:days] + month + months_row[(days + month_len):]
        else:
            days_row += days_chars[cur_date.weekday()]

        daybefore = cur_date

    months_row = months_row[:calendar_columns]  # chop off any extra spaces created by adding the months
    if use_color:
        months_row = style(months_row, fg=foreground, bg=header_color)
        days_row = style(days_row, fg=foreground, bg=header_color)
    months_row = (' ' * title_width) + (' ' * len(spacer)) + months_row
    days_row = (' ' * title_width) + (' ' * len(spacer)) + days_row
    click.echo(months_row)
    click.echo(days_row)

    # build shows rows
    step = 3
    color_row = False
    counter = 1
    season_marker = '-'
    filter_date = ''
    filter_name = ''
    if sort_by_next:
        filter_date = True
    if show_name:
        filter_name = show_name

    show = Shows(name_filter=filter_name, by_date=filter_date)
    for show in show:
        broadcast_row = ''
        title = show.db_name[:title_width].ljust(title_width)
        has_episode = False
        first_display_date = True
        last_days_away = 0
        last_date = 0
        for i in show.series:  # season
            for j in show.series[i]:  # episode
                episode_number = show.series[i][j]['airedEpisodeNumber']
                b_date = show.series[i][j]['firstAired']
                if not b_date:
                    continue  # some episode have no broadcast date?
                split_date = b_date.split('-')
                broadcast_date = datetime.datetime(
                    int(split_date[0]), int(split_date[1]), int(split_date[2]))
                if broadcast_date == last_date:
                    continue  # sometimes multiple episodes have the same date, don't repeat them.
                last_date = broadcast_date
                if broadcast_date.date() < today.date():
                    continue  # don't include episodes before today
                days_away = (broadcast_date - today).days + 1
                if days_away >= calendar_columns:
                    continue  # don't include days after the width of the screen
                if show.series[i][j]['airedSeason'] == '0':
                    continue  # not interested in season 0 episodes.

                if first_display_date:
                    if int(episode_number) > 1:
                        before_first = season_marker * days_away
                    else:
                        before_first = ' ' * days_away
                    broadcast_row = before_first + episode_number
                    first_display_date = False
                    # set the next episode date in the db while we're here:
                    show.set_next_episode(broadcast_date.date())
                else:
                    episode_char_len = len(str(int(episode_number) - 1))
                    broadcast_row = broadcast_row + (
                        season_marker * (days_away - last_days_away - episode_char_len)) + episode_number

                last_days_away = days_away

                has_episode = True

        broadcast_row = broadcast_row[:calendar_columns].ljust(calendar_columns)

        if has_episode or show_all:
            if use_color and color_row:
                title = style(title, fg=foreground, bg=title_color_1)
                broadcast_row = style(broadcast_row, fg=foreground, bg=date_color_1)
            elif use_color and not color_row:
                title = style(title, fg=foreground, bg=title_color_2)
                broadcast_row = style(broadcast_row, fg=foreground, bg=date_color_2)
            row = title + spacer + broadcast_row
            click.echo(row)

            if counter >= step:
                counter = 0
                color_row = True
            else:
                color_row = False
                counter += 1
