ARG IMAGE_UBUNTU_21_04
#hadolint ignore=DL3006
FROM ${IMAGE_UBUNTU_21_04}

SHELL ["/bin/bash", "-c"]
ENV DEBIAN_FRONTEND=noninteractive LC_ALL=C.UTF-8 LANG=C.UTF-8 PATH="/opt/bin:${PATH}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends apt-utils \
    && apt-get install -y \
    ansible \
    git \
    python2 \
    python3-pip \
    python-pip-whl \
    && \
    ansible-galaxy collection install community.general \
    && rm -rf /var/lib/apt/lists/*

# both versions required
RUN pip3 install ansible
RUN pip3 install boto
RUN pip3 install boto3

# Ensure all our build containers have the jenkins user (with same uid/gid). The non privileged
# jobs will be executed as this user in the container
RUN groupadd -g 1000 jenkins \
    && useradd -m -u 1001 -g 1000 -s /bin/bash jenkins