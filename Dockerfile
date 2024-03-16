# hadolint ignore=DL3007
FROM levaitamas/vobsub2srt:latest as vobsub2srt_builder

FROM python:3.11-slim-bookworm

WORKDIR /
COPY --from=vobsub2srt_builder /usr/local/bin/vobsub2srt /usr/bin/vobsub2srt
COPY --chown=user:user requirements.txt requirements.txt

RUN apt-get update && apt-get install --no-install-recommends -y \
    diffutils=1:3.8-4 \
    ffmpeg=7:5.1.4-0+deb12u1 \
    tesseract-ocr=5.3.0-2 \
    tesseract-ocr-eng=1:4.1.0-2 \
    libtesseract5=5.3.0-2 \
    mkvtoolnix=74.0.0-1 \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN pip install --no-cache-dir --requirement requirements.txt \
    && rm requirements.txt

RUN groupadd user --gid 1000 \
    && useradd user --uid 1000 --gid 1000 \
    && mkdir --parents /data/all_subtitles_dir/{modified,original}/{MakeMKV,OST} \
    && mkdir --parents /data/{jellyfin_Shows,MakeMKV_dir,csv_dir} \
    && touch /data/MKV_Namer_history.csv \
    && chmod 777 -R /data \
    && chown user:user -R /data

USER user
COPY --chown=user:user --chmod=755 scripts/ /scripts
WORKDIR /scripts

ENV MakeMKV_dir=MakeMKV_dir \
    renamed_dir=jellyfin_Shows \
    all_subtitles_dir=all_subtitles_dir \
    csv_dir=csv_dir \
    match_threshold=75 \
    rename=False \
    show_matches=False

ENTRYPOINT [ "tail", "-f", "/dev/null" ]
