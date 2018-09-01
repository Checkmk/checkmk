FROM debian:stretch-slim
LABEL maintainer="feedback@check-mk.org"

# Pure build time variable declarations (docker build --build-arg KEY=val)
ARG CMK_VERSION="1.6.0i1"
# Choose one of: raw, enterprise, managed
ARG CMK_EDITION="raw"

ARG CMK_DL_URL="https://mathias-kettner.de/support"
# Give download credentials in "USER:PASSWORD" format. You can only use Raw Edition without
ARG CMK_DL_CREDENTIALS=""

# The following variables can be set during container init (docker run -e KEY=val)
ARG CMK_SITE_ID
ENV CMK_SITE_ID="cmk"
# Set this to "on" to enable livestatus via network
ARG CMK_LIVESTATUS_TCP
ENV CMK_LIVESTATUS_TCP=""
# A random password will be generated in case you don't set this
ARG CMK_PASSWORD
ENV CMK_PASSWORD=""

# Specify the FQDN of your relay mail server to sent mails to
ARG MAIL_RELAY_HOST
ENV MAIL_RELAY_HOST=""

# Make the list of required packages available to the following command
COPY needed-packages /needed-packages

# First install the tools we need for fetching the package and installation
# Then fetch the package and install it. This will make sure all Check_MK
# containers will share all dependencies, including this step.
# hadolint ignore=SC2046,DL3008
RUN set -e \
    && echo "exit 101" > /usr/sbin/policy-rc.d \
    && chmod +x /usr/sbin/policy-rc.d \
    && export DEBIAN_FRONTEND=noninteractive \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        postfix \
        inetutils-syslogd \
        bsd-mailx \
        $(cat needed-packages) \
    && apt-get clean \
    && rm /usr/sbin/policy-rc.d \
    && rm -rf /var/lib/apt/lists/* \
    && rm needed-packages

# Now install the Check_MK version specific things
# TODO: Verify gpg signature
# hadolint ignore=DL3003,DL3008,DL4006
RUN set -e \
    && echo "exit 101" > /usr/sbin/policy-rc.d \
    && chmod +x /usr/sbin/policy-rc.d \
    && export DEBIAN_FRONTEND=noninteractive \
    && PKG_NAME="check-mk-${CMK_EDITION}-${CMK_VERSION}" \
    && PKG_FILE="${PKG_NAME}_0.stretch_$(dpkg --print-architecture).deb" \
    && echo "--user \"${CMK_DL_CREDENTIALS}\"" \
        | curl -o "${PKG_FILE}" -K - "${CMK_DL_URL}/${CMK_VERSION}/${PKG_FILE}" \
    && mkdir -p /usr/share/man/man8 \
    && dpkg -i "${PKG_FILE}" \
    && rm -f "${PKG_FILE}" \
    && apt-get clean \
    && rm /usr/sbin/policy-rc.d \
    && rm -rf /var/lib/apt/lists/*

LABEL \
    org.opencontainers.image.title="Check_MK" \
    org.opencontainers.image.version="${CMK_VERSION}" \
    org.opencontainers.image.description="Check_MK is a leading tool for Infrastructure & Application Monitoring" \
    org.opencontainers.image.vendor="Mathias Kettner GmbH" \
    org.opencontainers.image.source="https://git.mathias-kettner.de/" \
    org.opencontainers.image.url="https://mathias-kettner.com/"

# Ports:
# 5000 - Serves the Check_MK GUI
# 6557 - Serves Livestatus (if enabled via "omd config")
EXPOSE 5000 6557

# When all processes of the site are running everything should be fine
HEALTHCHECK --interval=1m --timeout=5s \
    CMD omd status || exit 1

COPY docker-entrypoint.sh /
# Starts the entrypoint script and hands over CMD by default
ENTRYPOINT ["/docker-entrypoint.sh"]
