#!/bin/bash

#
# Script to install agent and mk-job on Mac OSX
#

# Init
USER=$(whoami)
DEST_AGENT_PATH=/usr/local/lib/check_mk_agent
MK_JOB_OUTPUT_PATH=/var/lib/check_mk_agent/job
DEST_BIN_PATH=/usr/local/bin
SRC_PATH=../agents

# Install dependencies
brew install smartmontools osx-cpu-temp gnu-time

# Modify the plist file (remove cwd which was causing a launch error of "can't change to working dir")
sed -i '' '/<key>WorkingDirectory/{N;d;}' LaunchDaemon/de.mathias-kettner.check_mk.plist

# Create directories needed
mkdir -p "$DEST_AGENT_PATH"
mkdir -p "$DEST_AGENT_PATH/local"
mkdir -p "$DEST_AGENT_PATH/plugins"
sudo mkdir /etc/check_mk
sudo mkdir -p "${MK_JOB_OUTPUT_PATH}/${USER}"

# Copy files to required location
cp "{$SRC_PATH}/check_mk_agent.macosx" "${DEST_AGENT_PATH}/"
cp "{$SRC_PATH}/mk-job" "${DEST_AGENT_PATH}/"
sudo cp ../LaunchDaemon/de.mathias-kettner.check_mk.plist /Library/LaunchDaemons/
ln -s "${DEST_AGENT_PATH}/check_mk_agent.macosx" "${DEST_BIN_PATH}/check_mk_agent"
ln -s "${DEST_AGENT_PATH}/mk-job" "${DEST_BIN_PATH}/mk-job"
sudo touch /var/run/de.arts-others.softwareupdatecheck
sudo touch /var/log/check_mk.err

# Permissions: agent
chmod +x "${DEST_AGENT_PATH}/check_mk_agent.macosx"
sudo chmod +rw /var/run/de.arts-others.softwareupdatecheck
sudo chmod +rw /var/log/check_mk.err
sudo chown -R root:admin "$DEST_AGENT_PATH"

# Permissions: launch daemon
sudo chmod 644 /Library/LaunchDaemons/de.mathias-kettner.check_mk.plist

# Permissions: mk-job
sudo chown "$USER" "${MK_JOB_OUTPUT_PATH}/${USER}"
sudo chmod +rx "$(dirname $MK_JOB_OUTPUT_PATH)"
sudo chmod +rx "$MK_JOB_OUTPUT_PATH"

# Install LaunchDaemon
sudo launchctl load -w /Library/LaunchDaemons/de.mathias-kettner.check_mk.plist
