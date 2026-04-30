FROM ubuntu:22.04

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
    libgl1 \
    libglib2.0-0 \
    poppler-utils \
    libgomp1 \
    ocrmypdf \
    tesseract-ocr \
    tesseract-ocr-hrv \
    ghostscript \
    qpdf \
    jbig2dec \
    pngquant \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir --upgrade pip setuptools wheel

RUN pip3 install --no-cache-dir paddlepaddle==2.6.2

COPY requirements.txt /tmp/paddleocr-requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/paddleocr-requirements.txt \
    && rm -f /tmp/paddleocr-requirements.txt

WORKDIR /workspace/PaddleOCR

CMD ["sleep", "infinity"]
