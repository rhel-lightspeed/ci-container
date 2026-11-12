# 2026-11-09
FROM registry.access.redhat.com/ubi10-minimal:10.2-1794227009@sha256:f0c7b9ae9914fcf183e7c36fc46864903c2d2caf3af327421913ae54b3d29e94

ARG UID=1001
ARG TARGETARCH
ARG RLP_VERSION=0.30.1

RUN microdnf -y --nodocs --setopt install_weak_deps=0 install \
        git \
        jq \
        make \
        nc \
        podman \
        python-unversioned-command \
        python3 \
        python3-dnf \
        skopeo \
        socat \
    && microdnf clean all \
    && rpm -Uvh https://github.com/cli/cli/releases/download/v2.100.0/gh_2.100.0_linux_${TARGETARCH}.rpm

# Install rpm-lockfile-prototype for building an rpm lock file.
RUN python -m venv --system-site-packages /opt/venvs/rpm-lockfile \
    && /opt/venvs/rpm-lockfile/bin/pip install https://github.com/konflux-ci/rpm-lockfile-prototype/archive/refs/tags/v${RLP_VERSION}.tar.gz \
    && ln -s /opt/venvs/rpm-lockfile/bin/rpm-lockfile-prototype /usr/local/bin

ADD files/bin /usr/local/bin

ENV HOME=/var/lib/ci

RUN useradd --key HOME_MODE=0775 --uid ${UID} --gid 0 --create-home --home-dir "${HOME}" ci

USER ci
WORKDIR $HOME
