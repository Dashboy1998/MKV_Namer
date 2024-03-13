# Required Directory Structure
```
MakeMKV_dir
├── Series (2010) (tmdbid-123456)
│   ├── Season 01
│   │   ├── DISC_LABEL
│   │   │   ├── B1_t00.mkv
│   │   │   ├── B2_t01.mkv
│   └── Season 02
│   │   ├── DISC_LABEL
│   │   │   ├── B1_t00.mkv
│   │   │   ├── B2_t01.mkv
├── Series (1966) (tmdbid-654321)
│   ├── Season 01
│   │   ├── DISC_LABEL
│   │   │   ├── B1_t00.mkv
│   │   │   ├── B2_t01.mkv
│   └── Season 02
│   │   ├── DISC_LABEL
│   │   │   ├── B1_t00.mkv
│   │   │   ├── B2_t01.mkv
```

# How does it work
This program will use FFMPEG (FFPROBE) on every MKV to find the first SRT in english. If an SRT is not found then it will search for the first english VOBDVD/PGS.

SRTs will be extracted using [FFMPEG](https://github.com/FFmpeg/FFmpeg).

VOBDVD will be extracted using mkvextract and then converted to SRT using [vobsub2srt](https://github.com/ruediger/VobSub2SRT/tree/master).

PGS will be extracted and converted to SRT using [pgsrip](https://github.com/ratoaq2/pgsrip).

then using [tmdbsimple](https://github.com/celiao/tmdbsimple) it will get the list of episodes for every season listed in your directory structure.

then using [opensubtitlescom](https://github.com/dusking/opensubtitles-com) it will download subtitles for all episodes in a given season

then using sdiff it will compare your video's subtitles to the downloaded subtitles to find a match and name your videos.

# Enviromental Variables
| Variable | Info | Default Values | Allowed Values |
|-|-|-|-|
| TMDB_API_KEY | [The Movie Database](https://www.themoviedb.org/settings/api) API Key | None | String |
| OST_API_KEY | [Open Subtitles](https://www.opensubtitles.com/en/consumers) API Key | None | String |
| OST_USERNAME | [Open Subtitles](https://www.opensubtitles.com/en/) username | None | String |
| OST_PASSWORD | [Open Subtitles](https://www.opensubtitles.com/en/) password | None | String |
| match_threshold | Threshold Required for a match | 75 | Float |
| rename | Enables renaming MKV files | False | True/False |
| show_matches | Enables showing matches | False | True/False |

# Volume Mounts
## /data/
> [!TIP]
> For better performance do not use separate volumes in docker for [MakeMKV_dir](#/data/MakeMKV_dir) &
> [jellyfin_Shows](#/data/jellyfin_Shows) as this will result in a copy then delete instead of a rename.

Please mount your directory containing [MakeMKV_dir](#/data/MakeMKV_dir) & [jellyfin_Shows](#/data/jellyfin_Shows)
Output Directory used for matches.csv

## /data/MakeMKV_dir
Input directory with MKV files must have the [Required Directory Structure](#required_directory_structure)

## /data/jellyfin_Shows
Output directory which MKVs are moved to when a match is found and if rename is enabled.

## /data/all_subtitles_dir/
Output directory to store subtitles and text files. Files are not deleted.

# Running program
With the container started run `docker exec mkv_namer python MKV_Namer.py`

## Undoing rename
With the container started run `docker exec mkv_namer bash undo_move.sh`
