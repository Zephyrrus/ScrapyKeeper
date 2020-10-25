#
# Dockerfile for scrapyd:py3
#

FROM ubuntu:bionic

RUN set -xe \
    && apt-get update \
    && apt-get install -y autoconf \
                          build-essential \
                          curl \
                          git \
                          libffi-dev \
                          libssl-dev \
                          libtool \
                          libxml2 \
                          libxml2-dev \
                          libxslt1.1 \
                          libxslt1-dev \
                          python3 \
                          python3-dev \
                          python3-distutils \
                          vim-tiny \
                          zlib1g \
                          zlib1g-dev \
                          sqlite3 \
                          libmysqlclient-dev \
    && curl -sSL https://bootstrap.pypa.io/get-pip.py | python3 \
    && pip install git+https://github.com/scrapy/scrapyd.git \
                   git+https://github.com/scrapy/scrapyd-client.git

ENV TZ=UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY . /crawlie-keeper
WORKDIR /crawlie-keeper
RUN pip install -r requirements.txt

EXPOSE 5050

CMD ["python3", "entrypoint.py", "--no-auth"]
