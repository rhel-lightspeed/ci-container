# 2026-11-02
FROM registry.access.redhat.com/ubi10-minimal:10.2-1793642335@sha256:c039ecb9ac9db2db85e78b332d66521f6ce401cf812006a27bc7827018eac4a2

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
