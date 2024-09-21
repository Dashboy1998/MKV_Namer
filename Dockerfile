# hadolint ignore=DL3007
FROM debian:12-slim as vobsub2srt_builder

RUN apt-get update \
    && apt-get install --no-install-recommends -y git ca-certificates libtiff5-dev libtesseract-dev build-essential cmake pkg-config wget \
    && wget https://github.com/tesseract-ocr/tessdata_best/raw/main/eng.traineddata -O /usr/share/tesseract-ocr/5/tessdata/eng.traineddata \
    && git clone https://github.com/ecdye/VobSub2SRT.git VobSub2SRT \
    && cd VobSub2SRT \
    && git checkout f3205f54448505e56daaf7449fdddc1a4d036d50 \
    && sed -Ei 's/#include <vector>/#include <vector>\n#include <climits>/' src/vobsub2srt.c++ \
    && ./configure \
    && make -j`nproc` \
    && make install \
    && make distclean \
    && cd .. \
    && rm -rf VobSub2SRT \
    && strip /usr/local/bin/vobsub2srt \
    && apt-get purge -y git ca-certificates cmake pkg-config build-essential wget \
    && apt-get autoremove -y \
    && apt-get clean

FROM python:3.11-slim-bookworm

WORKDIR /
COPY --from=vobsub2srt_builder /usr/local/bin/vobsub2srt /usr/bin/vobsub2srt
COPY --chown=user:user requirements.txt requirements.txt

RUN apt-get update && apt-get install --no-install-recommends -y \
    diffutils=1:3.8-4 \
    ffmpeg=7:5.1.6-0+deb12u1 \
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
