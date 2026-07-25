# 2026-07-20
FROM registry.access.redhat.com/ubi10-minimal:10.2-1784581369@sha256:1de153ac8a6cb7793a57c837d5cb290c9a14296cb88d07fc3cc1a400f84d9231

ARG UID=1001

RUN microdnf -y --nodocs install \
        git \
        jq \
        nc \
        podman \
        socat \
    && microdnf clean all

ADD files/bin /usr/local/bin

ENV HOME=/var/lib/ci

RUN useradd --key HOME_MODE=0775 --uid ${UID} --gid 0 --create-home --home-dir "${HOME}" ci

USER ci
WORKDIR $HOME
