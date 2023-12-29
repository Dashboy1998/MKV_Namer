#!/bin/python

import os
import glob
from ffmpeg.asyncio import FFmpeg
import asyncio
import re


MakeMKV_dir="/home/cmartinez/Personal/Temp/RIPs/rip_sub/"
all_subtitles_dir="/home/cmartinez/Documents/MakeMKV_Namer/all_subtitles/"

MakeMKV_subtitles=all_subtitles_dir + 'original/MakeMKV/'

def generate_mkv_subtitles_folders():
    return_dirnames=[]
    return_filenames=[]
    for dirpath, dirnames, filenames in os.walk(MakeMKV_dir):
        # Create directories to store SRTs
        return_dirnames = return_dirnames + dirnames
        return_filenames.append(filenames)
        for dirname in dirnames:
            print(dirname)
            print("\t" + MakeMKV_dir)
            print("\t" + dirpath)
            newpath = MakeMKV_subtitles + dirpath.replace(MakeMKV_dir, "") + "/" + dirname
            print("\t" + newpath)
            # if not os.path.exists(newpath):
            #     os.makedirs(newpath)
    print(return_dirnames)
    print(return_filenames)
    return return_dirnames, return_filenames


# ffmpeg -i input.mkv -map 0:s:0 output.srt    
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
                    print(video_path)
                    #asyncio.run(run_ffmpeg(srt_name, video_path))


dirnames, filenames = generate_mkv_subtitles_folders()
#generate_mkv_subtitles(dirnames, filenames)


