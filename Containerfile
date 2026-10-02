# 2026-09-30
FROM registry.access.redhat.com/ubi10-minimal:10.2-1790753097@sha256:204e1531cee54562b107fb31e0b327062fc3d5d67af7cc0d2e66b2c572b9044f

ARG UID=1001
ARG TARGETARCH

RUN microdnf -y --nodocs install \
        git \
        jq \
        make \
        nc \
        podman \
        python3 \
        socat \
    && microdnf clean all \
    && rpm -Uvh https://github.com/cli/cli/releases/download/v2.100.0/gh_2.100.0_linux_${TARGETARCH}.rpm

ADD files/bin /usr/local/bin

ENV HOME=/var/lib/ci

RUN useradd --key HOME_MODE=0775 --uid ${UID} --gid 0 --create-home --home-dir "${HOME}" ci

USER ci
WORKDIR $HOME
