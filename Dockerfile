FROM archlinux

# Install packages
RUN pacman -Sy
RUN pacman --noconfirm -S \
    diffutils \
    ffmpeg \
    tesseract-data-eng \
    mkvtoolnix-cli \
    python-pip \
    base-devel \
    git \
    cmake

RUN groupadd user --gid 1000 && \
    useradd user --uid 1000 --gid 1000 -m && \
    mkdir -p /all_subtitles/{modified,original}/{MakeMKV,OST} && \
    chown user:user -R /all_subtitles && \
    mkdir -p /output/jellyfin_Shows && \
    chown user:user -R /output && \
    mkdir /MakeMKV_dir && \
    chown user:user -R /MakeMKV_dir

# Prepare build for vobsub2srt
USER user
WORKDIR /home/user
RUN git clone https://aur.archlinux.org/vobsub2srt-git.git
WORKDIR /home/user/vobsub2srt-git

# Build vobsub2srt
RUN makepkg -r -c

# Install vobsub2srt
USER root
RUN pacman --noconfirm -U ./vobsub2srt-git-1.0.7.gf3205f5-1-x86_64.pkg.tar.zst

# Cleanup
WORKDIR /home/user
RUN pacman --noconfirm -R \
    base-devel \
    git \
    cmake && \
    rm -rf vobsub2srt-git

# Install pip packages
USER user
WORKDIR /home/user
COPY --chown=user:user requirements.txt requirements.txt
COPY --chown=user:user --chmod=755 scripts/ scripts
RUN pip install --break-system-packages --no-cache-dir --upgrade pip && \
    pip install --break-system-packages --no-cache-dir --requirement requirements.txt && \
    rm requirements.txt

ENTRYPOINT [ "tail", "-f", "/dev/null" ]
