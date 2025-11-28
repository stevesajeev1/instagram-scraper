FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y software-properties-common && \
    add-apt-repository -y ppa:mozillateam/ppa

RUN printf "Package: firefox*\nPin: release o=LP-PPA-mozillateam\nPin-Priority: 1001\n" \
    > /etc/apt/preferences.d/mozilla-firefox

RUN apt-get update && \
    apt-get install -y firefox xvfb imagemagick curl && \
    rm -rf /var/lib/apt/lists/*

COPY profile /profile

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]