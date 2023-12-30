#!/bin/python

import srt
import os
import glob
from ffmpeg.asyncio import FFmpeg
import asyncio
import tmdbsimple as tmdb
from opensubtitlescom import OpenSubtitles
import re

match="*.srt"
output_ext="txt2"

opensubtitles_api_key=os.environ['OST_API_KEY']
opensubtitles_username=os.environ['OST_USERNAME']
opensubtitles_password=os.environ['OST_PASSWORD']
tmdb_api_key=os.environ['TMDB_API_KEY']
MakeMKV_dir=os.environ['MakeMKV_dir']
all_subtitles_dir=os.environ['all_subtitles_dir']

MakeMKV_subtitles=all_subtitles_dir + 'original/MakeMKV/'

def process_srts():
    srt_files = glob.glob('**/' + match, recursive=True)
    print(srt_files)

    for file in srt_files:
        srt_all = ""
        with open(file) as f:
            # Find all blocks
            for line in f:
                srt_all+=line
        out_file = file + 'txt2'
        with open(out_file, "a") as f:
            subtitle_generator = srt.parse(srt_all)
            subtitles = list(subtitle_generator)
            for subtitle in subtitles:
                f.write(subtitle.content.replace('\n',' ') + '\n')


class Series:
    def __init__(self, name="", tmdb_id="", seasons=[], first_air_date=""):
        self.name=str(name)
        self.tmdb_id=str(tmdb_id)
        self.seasons=seasons
        # Assumes format is YYYY-MM-DD or YYYY-DD-MM
        self.year=str(first_air_date.split("-")[0])
    def set_year(self, first_air_date=""):
        # Assumes format is YYYY-MM-DD or YYYY-DD-MM
        self.year=str(first_air_date.split("-")[0])
    def get_save_dir(self):
        # TODO
        return ""
    def get_subtitles_save_dir(self):
        return self.name + " (" + self.year + ") [tmdbid-" + self.tmdb_id + "]/"


class Season:
    def __init__(self, season_number="", season_tmdb_id="", episodes=None):
        self.season_number=season_number
        self.season_tmdb_id=season_tmdb_id
        self.episodes = episodes if episodes else []
    def get_save_dir(self):
        # TODO
        return ""
    def get_subtitles_save_dir(self):
        return "Season " + str(self.season_number) + "/"

# class Show:
#     def __init__(self, name="", tmdb_id="", season_number="", episode_array=[], first_air_date=""):
#         self.name=str(name)
#         self.tmdb_id=str(tmdb_id)
#         self.season_number=season_number
#         self.episode_array=episode_array
#         # Assumes format is YYYY-MM-DD or YYYY-DD-MM
#         self.year=str(first_air_date.split("-")[0])


def get_information_from_tmdb(MY_API_KEY, series_list):
    # Search for title on OST
    tmdb.API_KEY = tmdb_api_key

    search = tmdb.Search()
    for series in series_list:
        response = search.tv(query=series.name)

        # TODO Remove leading zeros from ID
        series.tmdb_id = str(search.results[0]['id'])
        if series.tmdb_id[0] == 0:
            print("TMDB ID Beigns with a 0!, not designed to remove the leading zeros yet")
        series.name = search.results[0]['original_name']
        series.set_year(search.results[0]['first_air_date'])

        for season in series.seasons:
            tv = tmdb.TV_Seasons(series.tmdb_id, season.season_number)
            response = tv.info()
            # Season ID
            season.season_tmdb_id = response['id']

            # Number of episodes
            for episode in response['episodes']:
                # Episode number stored in array instead of doing len() due to possibly of fraction or zero number episodes
                season.episodes.append(episode['episode_number'])
                # TODO Implement episode types
                if episode['episode_type'] != "standard":
                    print("Series: " + series.name + " Season: " + season.season_number)
                    print("\tEpisode type is not standard!: ")
                    print("\t" + str(episode['episode_number']))
                    print("\t" + episode['episode_type'])
    return series_list

# def get_subtitles(MY_API_KEY, my_show):
#     # Get subtitles
#     # Initialize the OpenSubtitles client
#     subtitles = OpenSubtitles("Identify", MY_API_KEY)

#     # Search for subtitles
#     for episode_number in my_show.episode_array:
#         response = subtitles.search(parent_tmdb_id=my_show.tmdb_id, season_number=my_show.season_number, episode_number=episode_number, languages="en")

#         # Convert the response to a Python dictionary
#         # response_dict = response.to_dict()
#         # save_as="All_Subs/" + series_name + " S" + str(my_show.season_number) + " E" + str(episode_number)
#         # srt = subtitles.download_and_save(response.data[0], filename=save_as)

def get_subtitles(MY_API_KEY, series_list):
    # Get subtitles
    # Initialize the OpenSubtitles client
    subtitles = OpenSubtitles("Identify", MY_API_KEY)
    # Log in (retrieve auth token)
    subtitles.login(opensubtitles_username, opensubtitles_password)

    for series in series_list:
        # TODO Create dir to save subtitles for series
        series_path = all_subtitles_dir + "original/OST/" + series.get_subtitles_save_dir()
        if not os.path.exists(series_path):
            os.makedirs(series_path)
        for season in series.seasons:
            # TODO Create dir to save subtitles for each season
            season_path = series_path + season.get_subtitles_save_dir()
            if not os.path.exists(season_path):
                os.makedirs(season_path)
            # Search for subtitles
            for episode_number in season.episodes:
                # TODO Add padding for episode number
                save_as = season_path + series.name + " E" + str(episode_number) + ".srt"
                if not os.path.exists(save_as):
                    response = subtitles.search(parent_tmdb_id=series.tmdb_id, season_number=season.season_number, episode_number=episode_number, languages="en")

                    srt = subtitles.download_and_save(response.data[0], filename=save_as)

def generate_mkv_subtitles_folders():
    return_dirnames=[]
    return_filenames=[]
    for dirpath, dirnames, filenames in os.walk(MakeMKV_dir):
        # Create directories to store SRTs
        return_dirnames = return_dirnames + dirnames
        return_filenames.append(filenames)
        for dirname in dirnames:
            newpath = MakeMKV_subtitles + dirname
            if not os.path.exists(newpath):
                os.makedirs(newpath)
    return return_dirnames, return_filenames


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


def generate_mkv_subtitles(dirnames, filenames):
    for i in range(len(filenames)):
        if i > 0:
            save_path = MakeMKV_subtitles + dirnames[i-1]
            for file in filenames[i]:
                srt_name = save_path + "/" + file.replace(".mkv",".srt")
                video_path = MakeMKV_dir + dirnames[i-1] + "/" + file

                if not os.path.isfile(srt_name):
                    asyncio.run(run_ffmpeg(srt_name, video_path))



def discover_series(dirnames):
    series_dict = dict()
    for dir_name in dirnames:
        # TODO Add lower case s
        series_name = re.search('.*(?= S[0-9]*)', dir_name).group(0)
        season_number = re.search('(?<= S)[0-9]*', dir_name).group(0)
        if not series_name in series_dict:
            series_dict[series_name]=[season_number]
        elif not season_number in series_dict[series_name]:
            series_dict[series_name].append(season_number)

    series_list=[]
    for series in series_dict:
        seasons = []
        for season in series_dict[series]:
            seasons.append(Season(season_number=season))
        series_list.append(Series(name=series,seasons=seasons))
    return series_list


dirnames, filenames = generate_mkv_subtitles_folders()
generate_mkv_subtitles(dirnames, filenames)
# Create list of series
series_list = discover_series(dirnames)
series_list = get_information_from_tmdb(tmdb_api_key, series_list)
# Get subtitles for each season

# season_show = get_information_from_tmdb(tmdb_api_key)
# print(season_show.name + " (" + season_show.year + ") [tmdbid-" + str(season_show.tmdb_id) + "]\n\tSeason " + str(season_show.season_number))


get_subtitles(opensubtitles_api_key, series_list)
# process_srts()


# dir_name="Hogan_s_Heroes_S3_D2"
# import re

# dir_name=dir_name.replace("_"," ")
# season_number = re.search('(?<= S)[0-9]*', dir_name).group(0)
# print(season_number)


