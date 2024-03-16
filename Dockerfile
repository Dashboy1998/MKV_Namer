FROM levaitamas/vobsub2srt:latest as vobsub2srt_builder

FROM python:3.11-slim-bookworm

COPY --from=vobsub2srt_builder /usr/local/bin/vobsub2srt /usr/bin/vobsub2srt
COPY --chown=user:user requirements.txt requirements.txt

RUN apt-get update \
    && apt-get install --no-install-recommends -y diffutils ffmpeg tesseract-ocr tesseract-ocr-eng libtesseract5 mkvtoolnix \
    && apt-get autoremove -y \
    && apt-get clean

RUN pip install --no-cache-dir --requirement requirements.txt \
    && rm requirements.txt

RUN groupadd user --gid 1000 \
    && useradd user --uid 1000 --gid 1000 \
    && mkdir --mode 777 --parents /data/all_subtitles/{modified,original}/{MakeMKV,OST} \
    && mkdir --mode 777 --parents /data/{jellyfin_Shows,MakeMKV_dir} \
    && touch /data/MKV_Namer_history.csv \
    && chown user:user -R /data

USER user
COPY --chown=user:user --chmod=755 scripts/ /scripts
WORKDIR /scripts

ENTRYPOINT [ "tail", "-f", "/dev/null" ]
