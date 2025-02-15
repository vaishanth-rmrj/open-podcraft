# docker file provided by Zyphra
FROM pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel
RUN pip install uv

RUN apt update && \
    apt install -y espeak-ng && \
    rm -rf /var/lib/apt/lists/*

# install additonal dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git git-lfs \
    nano vim less util-linux tree ffmpeg\
    htop atop nvtop \
    sed gawk grep curl wget tmux \
    x11-apps terminator \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /root/install
RUN mkdir -p /root/open-podcraft

# install Zonos package
WORKDIR /root/install
RUN git clone https://github.com/Zyphra/Zonos.git
WORKDIR /root/install/Zonos
RUN uv pip install --system -e . && uv pip install --system -e .[compile]

WORKDIR /root/open-podcraft
COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
