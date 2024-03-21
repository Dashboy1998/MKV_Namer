#!/bin/python

import asyncio
import json
import os
import re
import shutil
import subprocess
import sys

import srt
import tmdbsimple as tmdb
from babelfish import Language
from ffmpeg.asyncio import FFmpeg
from opensubtitlescom import OpenSubtitles
from pgsrip import Mkv, Options, pgsrip

opensubtitles_api_key = str(os.environ['OST_API_KEY'])
opensubtitles_username = str(os.environ['OST_USERNAME'])
opensubtitles_password = str(os.environ['OST_PASSWORD'])
tmdb_api_key = str(os.environ['TMDB_API_KEY'])
MakeMKV_dir = os.path.join('/data', str(os.environ['MakeMKV_dir']))
all_subtitles_dir = os.path.join('/data', str(os.environ['all_subtitles_dir']))
renamed_dir = os.path.join('/data', str(os.environ['renamed_dir']))
compare_srt_renaming_history = os.path.join('/data', str(os.environ['csv_dir']), 'MKV_Namer_history.csv')
matches_csv = os.path.join('/data', str(os.environ['csv_dir']), 'matches.csv')
match_threshold = float(os.environ['match_threshold'])
rename = os.environ['rename'].lower() in ('true')
show_matches = os.environ['show_matches'].lower() in ('true')

original_makemkv_subtitles = os.path.join(all_subtitles_dir, 'original/MakeMKV/')
modified_makemkv_subtitles = os.path.join(all_subtitles_dir, 'modified/MakeMKV/')
original_ost_subtitles = os.path.join(all_subtitles_dir, 'original/OST/')
modified_ost_subtitles = os.path.join(all_subtitles_dir, 'modified/OST/')


# Classes
class Series:
    def __init__(self, name='', tmdb_id='', first_air_date='', seasons=None):
        self.name = str(name)
        self.tmdb_id = str(tmdb_id)
        self.seasons = seasons if seasons else []
        # Assumes format is YYYY-MM-DD or YYYY-DD-MM
        self.year = str(first_air_date.split('-')[0])
        # TODO Add Unknown videos if season is unknown

    def set_year(self, first_air_date=''):
        # Assumes format is YYYY-MM-DD or YYYY-DD-MM
        self.year = str(first_air_date.split('-')[0])

    def get_path(self, parent_path = ''):
        # TODO
        return os.path.join(parent_path, '{0} ({1}) [tmdbid-{2}]'.format(self.name, self.year, self.tmdb_id))

    def get_subtitles_save_dir(self, parent_path=''):
        return os.path.join(parent_path, '{0} ({1}) [tmdbid-{2}]'.format(self.name, self.year, self.tmdb_id))

    def add_season(self, new_season):
        adding_season = True
        for i_season in self.seasons:
            if new_season.season_tmdb_id == i_season.season_tmdb_id:
                # Add unknown episodes
                i_season.unknown_videos = i_season.unknown_videos + new_season.unknown_videos
                # Exit series loop as we have found the series
                adding_season = False
                break
        if adding_season:
            self.new_season.append(new_season)

    def print_pretty(self, spacing=''):
        sys.stdout.write('{0}\n'.format(self.name))
        sys.stdout.write('{0}TMDB ID: {1}\n'.format(spacing, self.tmdb_id))
        sys.stdout.write('{0}Year: {1}\n'.format(spacing, self.year))
        sys.stdout.write('{0}Series Directory: {1}\n'.format(spacing, self.get_path()))
        sys.stdout.write('{0}Seasons: \n'.format(spacing))
        for season in self.seasons:
            season.print_pretty()


class Season:
    def __init__(self, season_number='', season_tmdb_id='', episodes=None, unknown_videos=None):
        self.season_number = season_number
        self.season_tmdb_id = season_tmdb_id
        self.episodes = episodes if episodes else []
        self.unknown_videos = unknown_videos if unknown_videos else []

    def get_path(self):
        return 'Season {0}'.format(str(self.season_number).zfill(2))

    def get_subtitles_save_dir(self, parent_path=''):
        return os.path.join(parent_path, 'Season {0}'.format(str(self.season_number).zfill(2)))

    def print_pretty(self, spacing='  '):
        sys.stdout.write('{0}Season {1}\n'.format(spacing, self.season_number))
        for episode in self.episodes:
            episode.print_pretty(spacing + spacing)
        for unknown_episode in self.unknown_videos:
            unknown_episode.print_pretty(spacing)


class Episode:
    # TODO Implement episode types
    def __init__(self, episode_number='', episode_type='', original_subtitles_file='', modified_subtitles_file='', num_lines=None):
        self.episode_number = episode_number
        self.episode_type = episode_type
        self.original_subtitles_file = original_subtitles_file
        self.modified_subtitles_file = modified_subtitles_file
        self.num_lines = num_lines

    def get_path(self, name, season_number, extension):
        return '{0} S{1}E{2}{3}'.format(name, str(season_number).zfill(2), str(self.episode_number).zfill(2), extension)

    def get_original_subtitles_path(self):
        return self.original_subtitles_file

    def get_modified_subtitles_path(self):
        return self.modified_subtitles_file

    def set_num_lines(self):
        self.num_lines = count_lines(self.modified_subtitles_file)

    def print_pretty(self, spacing):
        sys.stdout.write('{0}Episode: {1}\n'.format(spacing , self.episode_number))
        sys.stdout.write('{0}{0}Episode Type: {1}\n'.format(spacing, self.episode_type))


class Unknown_Video():
    def __init__(self, file='', original_subtitles_path='', modified_subtitles_path='', stream_num=-1, stream_codec='', match_dict=None):
        self.file = file
        self.original_subtitles_path = original_subtitles_path
        self.modified_subtitles_path = modified_subtitles_path
        self.stream_num = stream_num
        self.stream_codec = stream_codec
        self.match_dict =  match_dict if match_dict else {}

    def print_pretty(self, spacing):
        sys.stdout.write('{0}file: {1}\n'.format(spacing, self.file))
        sys.stdout.write('{0}{0}original_subtitles_path: {1}\n'.format(spacing, self.original_subtitles_path))
        sys.stdout.write('{0}{0}modified_subtitles_path: {1}\n'.format(spacing, self.modified_subtitles_path))
        sys.stdout.write('{0}{0}stream_num: {1}\n'.format(spacing, self.stream_num))
        sys.stdout.write('{0}{0}stream_codec: {1}\n'.format(spacing, self.stream_codec))


# Micro Functions
def count_lines(file_path):
    with open(file_path, 'r') as file:
        return sum(1 for _ in file)


def get_series_name(dirname):
    results = re.search('.*(?= \([0-9]*)', dirname)
    return results.group(0) if results else None


def get_series_year(dirname):
    # TODO Implement more than one year extracted
    results = re.findall(r'(\d+)', dirname)
    return results[0] if results else None


def get_series_tmdbid(dirname):
    # TODO Implement more than one TMDB ID extracted
    results = re.findall(r'[\[{]tmdbid-(\d+)[\]}]', dirname)
    return results[0] if results else None


def get_season_number(dirname):
    # TODO Implement unable to extract season number
    # TODO Implement more than one season extracted
    results = re.findall(r'\d+', dirname)
    return results[0]


# TMDB Functions
def get_series_information_from_tmdb(series_name, series_year, series_tmdb_id):
    # TODO Implement no results found
    # TODO Implement more than one result found
    # TODO Implement if given tmdb id and year but not name check if year is correct
    # TODO See if season information is given series call 
    # Note the number of seasons and amount of episodes in each season is returned in ['seasons'] however you will not know the number of each episode
    tmdb.API_KEY = tmdb_api_key

    series = None

    # Gets information if you have the TMDB ID
    if series_tmdb_id:
        tv = tmdb.TV(series_tmdb_id)
        response = tv.info()

        series_name = response['name']
        series_year = response['first_air_date']
        series = Series(series_name, series_tmdb_id, series_year)
    # Does a search for the series with the name and year if provided
    else:
        search = tmdb.Search()
        if series_name and series_year:    
            response = search.tv(query=series_name, first_air_date_year=series_year)
        elif series_name:
            response = search.tv(query=series_name)

        # TODO Remove leading zeros from ID
        series_tmdb_id = str(search.results[0]['id'])

        if series_tmdb_id[0] == 0:
            sys.stdout.write('TMDB ID Beigns with a 0!, not designed to remove the leading zeros yet\n')
        series_name = search.results[0]['original_name']
        series_year = (search.results[0]['first_air_date'])
        series = Series(series_name, series_tmdb_id, series_year)
    return series


def get_season_information_from_tmdb(season_number, series_tmdb_id):
    # TODO Implement no results found
    # TODO Implement too many results found
    # TODO Get all season information in one call
    # TODO See if series information is given season call 
    tmdb.API_KEY = tmdb_api_key

    tv = tmdb.TV_Seasons(series_tmdb_id, season_number)
    response = tv.info()

    # Season ID
    season_tmdb_id = response['id']

    # Getting Episode Information
    episodes = []
    for episode in response['episodes']:
        episodes.append(Episode(episode['episode_number'], episode['episode_type']))

    return Season(season_number, season_tmdb_id, episodes)


# OST Functions
def get_subtitles(series_list):
    # Get subtitles
    # Initialize the OpenSubtitles client
    subtitles = OpenSubtitles('Identify', opensubtitles_api_key)
    # Log in (retrieve auth token)
    subtitles.login(opensubtitles_username, opensubtitles_password)

    for series in series_list:
        for season in series.seasons:
            # Creating dirs to save subtitles for each season
            season_path = os.path.join(original_ost_subtitles, series.get_path(), season.get_path())
            os.makedirs(season_path, exist_ok=True)
            # Search for subtitles
            for episode in season.episodes:
                save_as = os.path.join(season_path, episode.get_path(series.name, season.season_number, '.srt'))
                if not os.path.exists(save_as):
                    # TODO Implement download limit reached
                    # TODO Implement no results found
                    response = subtitles.search(parent_tmdb_id=series.tmdb_id, season_number=season.season_number, episode_number=episode.episode_number, languages='en')
                    if response.data:
                        srt = subtitles.download_and_save(response.data[0], filename=save_as)
                    else:
                        sys.stdout.write('No subtitles found for {0} Season {1} Episode {2}\n'.format(series.name, season.season_number, episode.episode_number))
                if os.path.exists(save_as):
                    episode.original_subtitles_file = save_as
                    episode.modified_subtitles_file = os.path.join(modified_ost_subtitles, \
                                                      series.get_path(),
                                                      season.get_path(), \
                                                      episode.get_path(series.name, season.season_number, '.txt'))


def remove_empty_lines(input_string):
    lines = input_string.splitlines()
    non_empty_lines = [line for line in lines if line.strip()]
    return os.linesep.join(non_empty_lines)


# Processing Functions
def process_srt(input_file, output_file):
    # TODO Move creating output path
    output_path = os.path.dirname(output_file)
    os.makedirs(output_path, exist_ok=True)
    if not os.path.exists(output_file):
        srt_all = ''
        with open(input_file) as opened_file:
            # Find all blocks
            for line in opened_file:
                srt_all += line

        with open(output_file, 'a') as opened_file:
            subtitle_generator = srt.parse(srt_all)
            subtitles = list(subtitle_generator)
            for subtitle in subtitles:
                alphanumeric = re.sub('[^0-9a-zA-Z ]+', '', subtitle.content)
                word_per_line = alphanumeric.replace(' ', '\n')
                no_blank_lines = remove_empty_lines(word_per_line)
                opened_file.write('{0}\n'.format(no_blank_lines))


def process_srts(series_list):
    for series in series_list:
        for season in series.seasons:
            for unknown_video in season.unknown_videos:
                # Process SRTs
                process_srt( \
                    unknown_video.original_subtitles_path, \
                    unknown_video.modified_subtitles_path
                    )
            for episode in season.episodes:
                # Process SRTs
                process_srt( \
                    episode.get_original_subtitles_path(), \
                    episode.get_modified_subtitles_path()
                    )


# Get stream information from MKV file
async def get_media_info(file):
    ffmpeg = FFmpeg(executable='ffprobe').input(
            file,
            print_format='json',
            show_streams=None,
        )

    return await ffmpeg.execute()


# See if media has subtitles in correct format and return stream number
def get_srt_stream_number(file):
    media_info = json.loads( asyncio.run(get_media_info(file)))
    # sys.stdout.write({0\n}.format(str(json.dumps(media_info, indent = 4))))
    streams = media_info['streams']
    indexes = []
    languages = ['eng']
    codecs = ['subrip']
    index = -1
    for stream in streams:
        if stream['codec_type'] == 'subtitle':
            index = index + 1
            if stream['codec_name'] in codecs:
                if stream['tags']['language'] in languages:
                    indexes.append([index, stream['codec_name']])
    if len(indexes) == 0:
        # sys.stdout.write('SRT not found, searching for VOBDVD/PGS: {0}\n'.format(file))
        languages = ['eng']
        codecs = ['dvd_subtitle', 'hdmv_pgs_subtitle']
        index = -1
        for stream in streams:
            index = index + 1
            if stream['codec_type'] == 'subtitle':
                if stream['codec_name'] in codecs:
                    if stream['tags']['language'] in languages:
                        indexes.append([index, stream['codec_name']])
    if len(indexes) > 1:
        # TODO Better handling of multiple found
        sys.stdout.write('Ripping first found subtitle, Multiple subtitles found for the following for: {0}\n'.format(file))
    elif len(indexes) == 0:
        # TODO Better handling of not found
        sys.stdout.write('No subtitles found for: {0}\n'.format(file))

    if indexes:
        return indexes[0][0], indexes[0][1]  
    else:
        return -1, ''


async def run_ffmpeg(srt_name, video_path, stream_num):
    ffmpeg = (
            FFmpeg()
            .input(video_path)
            .output(
                srt_name,
                map=['0:s:{0}'.format(stream_num)],
                codec='text'
                )
        )

    await ffmpeg.execute()


def extract_vobsub(srt_name, video_path, stream_num):
    # Extract sub and idx
    subprocess.check_output(['mkvextract', '-q', 'tracks', video_path, '{0}:{1}'.format(stream_num, srt_name)])

    # Convert to SRT
    subprocess.check_output(['vobsub2srt', srt_name.replace('.srt', '') ])

    # Remove SUB and IDX files
    os.remove(srt_name.replace('.srt', '.idx'))
    os.remove(srt_name.replace('.srt', '.sub'))


def extract_pgs(srt_name, video_path, stream_num):
    media = Mkv(video_path)
    options = Options(languages={Language('eng')}, overwrite=True, one_per_lang=True)
    pgsrip.rip(media, options)
    srt_tmp_path = video_path.replace('.mkv', '.en.srt')
    shutil.move(srt_tmp_path, srt_name)


def extract_subtitles(series_list):
    # TODO Implement for no seasons but episodes
    for series in series_list:
        for season in series.seasons:
            for unknown_video in season.unknown_videos:
                original_subtitles_save_path = unknown_video.original_subtitles_path

                path = os.path.dirname(original_subtitles_save_path)
                os.makedirs(path, exist_ok=True)
                original_srt_name = unknown_video.original_subtitles_path


                codec_name = unknown_video.stream_codec

                if not os.path.isfile(original_srt_name):
                    # Check format name
                    # if SRT
                    if codec_name == 'subrip':
                        sys.stdout.write('Getting subrip from: {0}\n'.format(unknown_video.file))
                        asyncio.run(run_ffmpeg(original_srt_name, unknown_video.file, unknown_video.stream_num))
                    # Elif PGS
                    elif codec_name == 'dvd_subtitle':
                        sys.stdout.write('Getting vobdvd from: {0}\n'.format(unknown_video.file))
                        extract_vobsub(original_srt_name, unknown_video.file, unknown_video.stream_num)
                    # Elif VOBSUB (DVD)
                    elif codec_name == 'hdmv_pgs_subtitle':
                        sys.stdout.write('Getting pgs from: {0}\n'.format(unknown_video.file))
                        extract_pgs(original_srt_name, unknown_video.file, unknown_video.stream_num)
                    else:
                        sys.stdout.write('Unsupported subtitle format ({0}) for: {1}\n'.format(codec_name, unknown_video.file))
                        exit()
    return series_list


def discover_series():
    # TODO Iterate over directories to detect series and seasons
    series_list = []
    series_depth = 0
    season_depth = 1
    episode_depth = 2

    for root, _, files in os.walk(MakeMKV_dir):
        depth = root[len(MakeMKV_dir) + len(os.path.sep):].count(os.path.sep)
        # TODO Breaks if dirs does not end with /
        dirname = os.path.basename(root)

        if dirname: # Ignores root folder
            if depth == series_depth: # Series depth
                series_name = get_series_name(dirname)
                series_tmdbid = get_series_tmdbid(dirname)
                series_year = get_series_year(dirname)

                series = None
                if series_tmdbid and series_name and series_year:
                    series = Series(series_name, series_tmdbid, series_year)
                elif series_tmdbid or series_name:
                    # Read get missing information
                    series = get_series_information_from_tmdb(series_name, series_year, series_tmdbid)
                else:
                    # TODO Something useful other than just a print
                    sys.stdout.write('You are missing the series TMDB ID and name\n')
                if series:
                    # TODO Will attempt to add seasons resulting in an error
                    series_list.append(series)
            elif depth >= season_depth:
                if depth == season_depth:
                    season_number=get_season_number(dirname)

                    # Read Season
                    season = get_season_information_from_tmdb(season_number, series.tmdb_id)
                    series.seasons.append(season)
                if depth == episode_depth:
                    for file in files:
                        video_path = os.path.join(root, file)
                        stream_num, stream_codec = get_srt_stream_number(video_path)
                        if stream_num != -1:
                            original_subtitles_path = os.path.join(original_makemkv_subtitles, series_list[-1].get_path(), series_list[-1].seasons[-1].get_path(), dirname, file.replace('.mkv', '.srt'))
                            modified_subtitles_path = os.path.join(modified_makemkv_subtitles, series_list[-1].get_path(), series_list[-1].seasons[-1].get_path(), dirname, file.replace('.mkv', '.txt'))
                            series_list[-1].seasons[-1].unknown_videos.append(Unknown_Video(video_path, original_subtitles_path, modified_subtitles_path, stream_num, stream_codec))

    return series_list


def find_matches(series_list):
    for series in series_list:
        for season in series.seasons:
            for unknown_video in season.unknown_videos:
                unknown_video_subtitles = unknown_video.modified_subtitles_path
                num_lines_unknown_video = count_lines(unknown_video_subtitles)
                match_found = False
                match_percentages = []
                for episode in season.episodes:
                    episode_subtitles = episode.modified_subtitles_file
                    output = subprocess.check_output(['bash', './compare_srts.sh', unknown_video_subtitles, episode_subtitles])
                    different_lines = int(output.decode('utf-8').strip())
                    percent_match = 100 - 100 * different_lines / num_lines_unknown_video
                    match_percentages.append(percent_match)
                    if percent_match >= match_threshold:
                        mv_name = os.path.join(series.get_path(renamed_dir), season.get_path(), \
                                      episode.get_path(series.name, season.season_number, '.mkv'))

                        # Add match to dict
                        unknown_video.match_dict[mv_name]=percent_match

                        with open(matches_csv, 'a') as opened_file:
                            opened_file.write('{0},{1},{2:.2f}\n'.format(unknown_video.file, mv_name, percent_match))

                        if show_matches:
                            episode_likely = episode.get_path(series.name, season.season_number, '')
                            unknown_video_local_path = unknown_video.file.replace(MakeMKV_dir, '')
                            sys.stdout.write('{0} --> {1} ({2:.2f}%)\n'.format(unknown_video_local_path, episode_likely, percent_match))

                        match_found = True
                if not match_found:
                    unknown_video_subtitles_local = unknown_video_subtitles.replace(modified_makemkv_subtitles, '')
                    # TODO Do more than just output answer
                    sys.stdout.write('Match not found for {0}\n'.format(unknown_video_subtitles_local))
                    match_percentages.sort(reverse=True)
                    sys.stdout.write('\tBest match: {0:.2f}%\n'.format(match_percentages[0]))
                    if len(match_percentages) > 1:
                        sys.stdout.write('\tSecond best match: {0:.2f}%\n'.format(match_percentages[1]))
                    sys.stdout.write('\tNumber of lines: {0}\n'.format(num_lines_unknown_video))

    return series_list


def remove_episodes_without_subtitles(series_list):
    episode_list = []
    for series in series_list:
        for season in series.seasons:
            for episode in season.episodes:
                if episode.original_subtitles_file:
                    episode_list.append(episode)
            season.episodes = episode_list

    return series_list


def rename_videos(series_list):
    for series in series_list:
        for season in series.seasons:
            for unknown_video in season.unknown_videos:
                if len(unknown_video.match_dict) > 1:
                    unknown_video_local_path = unknown_video.file.replace(MakeMKV_dir, '')
                    sys.stdout.write('Multiple matches for {0}\n'.format(unknown_video_local_path))
                    for fmv_name, fpercent_match in unknown_video.match_dict.items():
                        filename = os.path.basename(fmv_name)
                        sys.stdout.write('\t{0:.2f},{1}\n'.format(fpercent_match, filename))
                elif len(unknown_video.match_dict) == 1:
                    mv_name = next(iter(unknown_video.match_dict.keys()))
                    percent_match = next(iter(unknown_video.match_dict.values()))

                    # Create output folder if it does not exists
                    os.makedirs(os.path.dirname(mv_name), exist_ok=True)

                    # TODO Fix error with renaming files going too fast?
                    shutil.move(unknown_video.file, mv_name)
                    with open(compare_srt_renaming_history, 'a') as opened_file:
                        opened_file.write('{0},{1},{2:.2f}\n'.format(unknown_video.file, mv_name, percent_match))


def main():
    # TODO If no season is detected then set one season to -1 and download all
    # TODO Assign unknown videos to seasons -1

    # Create list of series
    series_list = discover_series()

    series_list = extract_subtitles(series_list)

    # Download Subtitles from OST
    get_subtitles(series_list)

    # Remove episodes with no subtitles
    series_list = remove_episodes_without_subtitles(series_list)

    # Converts subtites to text files for easier comparison
    process_srts(series_list)

    # Find matches
    series_list = find_matches(series_list)

    if rename:
        rename_videos(series_list)


if __name__ == '__main__':
    main()
