
from setuptools import setup

import sys
import platform
import re

version = re.search(
    "^__version__\s*=\s*'(.*)'",
    open('tvoverlord/tvol.py').read(),
    re.M
    ).group(1)

if sys.version_info[0] == 2:
    dividers = '!' * 40
    sys.exit("{}\nSorry, TVOverlord does not support python 2.\nUse: 'pip3 install tvoverlord' instead\n{}".format(dividers, dividers))

long_description = """
TV Overlord is a command line tool to download and manage TV shows from
newsgroups or bittorent. It will download nzb files or magnet links.

It searches multiple sites simultaneously and combines the results
into one list to select from.

TV Overlord keeps track of which shows have been downloaded and what
shows are available to download.

More information at https://github.com/8cylinder/tv-overlord"""


setup(
    name='tvoverlord',
    packages=[
        'tvoverlord',
        'tvoverlord/search_providers'
    ],
    package_data={
        'tvoverlord': ['config.ini'],
    },
    entry_points='''
        [console_scripts]
        deluge_done=tvoverlord.client_finished:deluge
        transmission_done=tvoverlord.client_finished:transmission
        qbittorrent_done=tvoverlord.client_finished:qbittorrent
        tvol=tvoverlord.tvol:tvol
    ''',
    # install_requires=[
    #     'tvdb_api',
    #     'beautifulsoup4',
    #     'feedparser',
    #     'requests',
    #     'python-dateutil',
    #     'click',
    # ] + ([
    #     'colorama',
    # ] if 'Windows' == platform.system() else []),
    install_requires=[
        'tvdb_api>=2.0',
        'beautifulsoup4',
        'feedparser',
        'requests',
        'python-dateutil',
        'click',
        'colorama',
    ],
    version=version,
    description='TV Overlord is a command line tool to download and manage TV shows from newsgroups or bittorent',
    long_description=long_description,
    license='MIT',
    author='Sheldon McGrandle',
    author_email='developer@8cylinder.com',
    url='https://www.tvoverlord.com',
    keywords=[],
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Environment :: Console',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: MacOS',
        'Operating System :: POSIX :: Linux',
        'Operating System :: Unix',
        'Operating System :: Microsoft :: Windows',
        'Topic :: Internet',
        'Topic :: Multimedia :: Video',
        'Natural Language :: English',
        'Development Status :: 5 - Production/Stable',
    ],
)


## build source dist and wheel:
# python3 setup.py sdist bdist_wheel
## upload to pypi:
# twine upload dist/*
## install for dev:
# pip install --editable .

# pyinstaller tvol.spec

# future windows builds:
# python3 setup.py bdist_wininst
# python3 setup.py register sdist bdist_wininst upload
