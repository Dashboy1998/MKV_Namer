#!/bin/python

import srt
import os
from ffmpeg.asyncio import FFmpeg
import asyncio
import tmdbsimple as tmdb
from opensubtitlescom import OpenSubtitles
import re
import subprocess

opensubtitles_api_key=os.environ['OST_API_KEY']
opensubtitles_username=os.environ['OST_USERNAME']
opensubtitles_password=os.environ['OST_PASSWORD']
tmdb_api_key=os.environ['TMDB_API_KEY']
MakeMKV_dir=os.environ['MakeMKV_dir']
all_subtitles_dir=os.environ['all_subtitles_dir']
results_file=os.environ['results_file']

original_MakeMKV_subtitles=all_subtitles_dir + 'original/MakeMKV/'
modified_MakeMKV_subtitles=all_subtitles_dir + 'modified/MakeMKV/'


# Classes
class Series:
    def __init__(self, name="", tmdb_id="", first_air_date="", seasons=None):
        self.name=str(name)
        self.tmdb_id=str(tmdb_id)
        self.seasons=seasons if seasons else []
        # Assumes format is YYYY-MM-DD or YYYY-DD-MM
        self.year=str(first_air_date.split("-")[0])
        # TODO Add Unknown videos if season is unknown
    def set_year(self, first_air_date=""):
        # Assumes format is YYYY-MM-DD or YYYY-DD-MM
        self.year=str(first_air_date.split("-")[0])
    def get_path(self, parent_path=""):
        # TODO
        return  parent_path + self.name + " (" + self.year + ") [tmdbid-" + self.tmdb_id + "]/"
    
    def get_subtitles_save_dir(self, parent_path = ""):
        return parent_path + self.name + " (" + self.year + ") [tmdbid-" + self.tmdb_id + "]/"

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


class Season:
    def __init__(self, season_number="", season_tmdb_id="", episodes=None, unknown_videos=None):
        self.season_number=season_number
        self.season_tmdb_id=season_tmdb_id
        self.episodes = episodes if episodes else []
        self.unknown_videos = unknown_videos if unknown_videos else []
    def get_path(self):
        return "Season " + str(self.season_number).zfill(2) + "/"
    def get_subtitles_save_dir(self, parent_path=""):
        return parent_path + "Season " + str(self.season_number).zfill(2) + "/"

class Episode:
    # TODO Implement episode types
    def __init__(self, episode_number="", episode_type="", original_subtitles_file="", modified_subtitles_file="", num_lines=None):
        self.episode_number=episode_number
        self.episode_type=episode_type
        self.original_subtitles_file=original_subtitles_file
        self.modified_subtitles_file=modified_subtitles_file
        self.num_lines=num_lines
    def get_path(self, name, season_number, extension):
        return name + " S" + str(season_number).zfill(2) + "E" + str(self.episode_number).zfill(2) + extension
    def get_subtitles_save_path(self, parent_path, extension=""):
        return parent_path + " E" + str(self.episode_number).zfill(2) + extension
    def get_original_subtitles_path(self):
        return self.original_subtitles_file
    def get_modified_subtitles_path(self):
        return self.modified_subtitles_file
    def set_num_lines(self):
        self.num_lines=count_lines(self.modified_subtitles_file)

class Unknown_Video():
    def __init__(self, file="", original_subtitles_path="", modified_subtitles_path=""):
        self.file=file
        self.original_subtitles_path=original_subtitles_path
        self.modified_subtitles_path=modified_subtitles_path


# Micro Functions
def count_lines(file_path):
    with open(file_path, 'r') as file:
        return sum(1 for _ in file)

def get_original_subtitles_path(ost):
    path = ""
    if ost:
        path = all_subtitles_dir + 'original/OST/'
    else:
        path = all_subtitles_dir + 'original/MakeMKV/'
    return path

def get_modified_subtitles_path(ost):
    path = ""
    if ost:
        path = all_subtitles_dir + 'modified/OST/'
    else:
        path = all_subtitles_dir + 'modified/MakeMKV/'
    return path

def get_file_name_only():
    # TODO
    return ""

def get_path(file_path):
    file = file_path.split("/")[-1]
    # TODO Change to remove last X charactors
    path = file_path.replace(file, "")
    return path

def create_dirs(path):
    if not os.path.isdir(path):
        os.makedirs(path)

def extract_season_number(unknown_season):
    # TODO Implement unable to extract season number
    return re.search('(?<= [sS])[0-9]*', unknown_season).group(0)

def extract_series_name(unknown_series):
    # TODO Implement unable to extract series name
    return re.search('.*(?= [sS][0-9]*)', unknown_series).group(0)


# TMDB Functions
def get_series_information_from_tmdb(series_name):
    # TODO Implement no results found
    tmdb.API_KEY = tmdb_api_key

    search = tmdb.Search()
    response = search.tv(query=series_name)

    # TODO Remove leading zeros from ID
    series_tmdb_id = str(search.results[0]['id'])
    
    if series_tmdb_id[0] == 0:
        print("TMDB ID Beigns with a 0!, not designed to remove the leading zeros yet")
    series_name = search.results[0]['original_name']
    series_year = (search.results[0]['first_air_date'])

    return Series(series_name, series_tmdb_id, series_year)

def get_season_information_from_tmdb(season_number, series_tmdb_id):
    # TODO Implement no results found
    # TODO Implement too many results found
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
    subtitles = OpenSubtitles("Identify", opensubtitles_api_key)
    # Log in (retrieve auth token)
    subtitles.login(opensubtitles_username, opensubtitles_password)

    for series in series_list:
        for season in series.seasons:
            # Creating dirs to save subtitles for each season
            season_path = get_original_subtitles_path(ost=True) + series.get_path() + season.get_path()
            if not os.path.exists(season_path):
                os.makedirs(season_path)
            # Search for subtitles
            for episode in season.episodes:
                save_as = season_path + episode.get_path(series.name, season.season_number, ".srt")
                if not os.path.exists(save_as):
                    # TODO Implement download limit reached
                    # TODO Implement no results found
                    response = subtitles.search(parent_tmdb_id=series.tmdb_id, season_number=season.season_number, episode_number=episode.episode_number, languages="en")
                    srt = subtitles.download_and_save(response.data[0], filename=save_as)
                episode.original_subtitles_file = save_as
                episode.modified_subtitles_file = get_modified_subtitles_path(ost=True) \
                                                + series.get_path() + season.get_path() \
                                                + episode.get_path(series.name, season.season_number, ".txt")


# Processing Functions
def process_srt(input_file, output_file):
    # TODO Move creating output path
    output_path = get_path(output_file)
    create_dirs(output_path)
    if not os.path.exists(output_file):
        srt_all = ""
        with open(input_file) as f:
            # Find all blocks
            for line in f:
                srt_all+=line
        
        with open(output_file, "a") as f:
            subtitle_generator = srt.parse(srt_all)
            subtitles = list(subtitle_generator)
            for subtitle in subtitles:
                f.write(subtitle.content.replace('\n',' ') + '\n')

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


# ffmpeg -i B3_t01.mkv -map 0:s:0 subs_3.srt    
async def run_ffmpeg(srt_name, video_path):
    ffmpeg = (
            FFmpeg()
            .input(video_path)
            .output(
                srt_name,
                map=["0:s:0"]
                )
        )

    await ffmpeg.execute()


def extract_subtitles(series_list):
    # TODO Implement for no seasons but episodes
    for series in series_list:
        for season in series.seasons:
            for unknown_video in season.unknown_videos:
                original_subtitles_save_path = unknown_video.original_subtitles_path
                
                path = get_path(original_subtitles_save_path)
                create_dirs(path)
                original_srt_name = unknown_video.original_subtitles_path
                
                if not os.path.isfile(original_srt_name):
                    asyncio.run(run_ffmpeg(original_srt_name, unknown_video.file))
    return series_list


def discover_series():
    # TODO Iterate over directories to detect series and seasons
    series_list = []
    
    for dirpath, dirnames, filenames in os.walk(MakeMKV_dir):
        dirname = dirpath.split("/")[-1]
        
        if dirname:
            # Extract series name
            series_name = extract_series_name(dirname)
            # Get information for series
            series = get_series_information_from_tmdb(series_name)

            # Get season for series
            season_number = extract_season_number(dirname)
            season = get_season_information_from_tmdb(season_number, series.tmdb_id)
            
            unknown_videos = []
            for file in filenames:
                video_path = os.path.join(dirpath, file)
                original_subtitles_path = get_original_subtitles_path(ost=False) + series.get_path() + season.get_path() + "/" +dirname + "/" + file.replace(".mkv", ".srt")
                modified_subtitles_path = get_modified_subtitles_path(ost=False) + series.get_path() + season.get_path() + "/" +dirname + "/" + file.replace(".mkv", ".txt")

                
                unknown_videos.append(Unknown_Video(video_path, original_subtitles_path, modified_subtitles_path))
            season.unknown_videos=unknown_videos


            # Check if series exists
            series_exists = False
            for t_series in series_list:
                # If series exists 
                    # then check if season exists
                # If series does not exist add season add series
                if series.tmdb_id == t_series.tmdb_id:
                    t_series.add_season(season)

                    # Exit series loop as we have found the series
                    series_exists = True
                    break
            
            if ( not series_exists ):
                series.seasons.append(season)
                series_list.append(series) 
    
    return series_list


def find_matches(series_list):
    # with open("tmp_" + results_file, "w") as f:
    #     f.write("MKVSRT,ORTSRT,MTOTAL,OTOTAL,DIFF,PERCENTAGE_DIFF\n")

    for series in series_list:
        for season in series.seasons:
            for unknown_video in season.unknown_videos:
                unknown_video_subtitles = unknown_video.modified_subtitles_path
                num_lines_unknown_video = count_lines(unknown_video_subtitles)
                match_found = False
                for episode in season.episodes:
                    episode_subtitles = episode.modified_subtitles_file
                    # # Count the numbers of lines in episode if it does not exist
                    # if not episode.num_lines:
                    #     episode.set_num_lines()
                    output = subprocess.check_output(["bash", "./compare_srts.sh", unknown_video_subtitles, episode_subtitles])
                    different_lines = int(output.decode('utf-8').strip())
                    percent_match = 100 - 100 * different_lines / num_lines_unknown_video
                    threshold = 75
                    if percent_match >= threshold:
                        # TODO Rename file
                        if match_found:
                            print("Conflict!")
                        match_found = True

def main():
    # TODO If no season is detected then set one season to -1 and download all
    # TODO Assign unknown videos to seasons

    # Create list of series
    series_list = discover_series()
    
    series_list = extract_subtitles(series_list)

    # Download Subtitles from OST
    get_subtitles(series_list)

    # Converts subtites to text files for easier comparison
    process_srts(series_list)

    # Find matches
    find_matches(series_list)


if __name__ == "__main__":
    main()