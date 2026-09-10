# 2026-09-09
FROM registry.access.redhat.com/ubi10-minimal:10.2-1788940913@sha256:26dc3089ab24491c1ba01ab92a7d502d181425b6021e362a07484daee696a3aa

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
