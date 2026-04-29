FROM nvidia/cuda:11.8.0-cudnn8-devel-ubuntu20.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Zagreb

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    git \
    build-essential \
    wget \
    ca-certificates \
    tzdata \
    libgl1-mesa-glx \
    libglib2.0-0 \
    poppler-utils \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --upgrade pip

RUN pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple paddlepaddle-gpu==2.5.1

COPY requirements.txt /tmp/paddleocr-requirements.txt
RUN pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple -r /tmp/paddleocr-requirements.txt \
    && rm -f /tmp/paddleocr-requirements.txt

WORKDIR /workspace/PaddleOCR

CMD ["bash"]
