PIPENV := ../../scripts/run-pipenv
RUN_IN_DOCKER := ../../scripts/run-in-docker.sh
THREE_TO_TWO := $(PIPENV) run 3to2

# New plugins are expected to all have a .py extension. This will discover them
# automatically.  Old plugins without extension are explicitly whitelistet here
# to be found.
PYTHON3_PLUGINS_WITHOUT_EXTENSION := apache_status \
    isc_dhcpd \
    mailman_lists \
    mk_inotify \
    mk_logwatch \
    mk_mongodb \
    mk_sap \
    mk_tinkerforge \
    mtr \
    nginx_status \
    plesk_backups \
    plesk_domains \
    unitrends_replication
PYTHON3_PLUGINS := $(PYTHON3_PLUGINS_WITHOUT_EXTENSION) $(wildcard *.py)

.PHONY: all clean

all: $(addsuffix .py2,$(PYTHON3_PLUGINS:.py=))

clean:
	$(RM) *.py2

%.py: $(findstring %, $(PYTHON3_PLUGINS_WITHOUT_EXTENSION))
	cp "$(@:.py=)" "$@"

%.py2: %.py
	cat "$<" | gawk -v text="# Do not test generated 2.6 files\n# yapf: disable\n# type: ignore" '!/^#/ && !p {print text; p=1} 1' > "$@"
	$(RUN_IN_DOCKER) $(THREE_TO_TWO) --nofix=str --nobackups --write "$@" >/dev/null
	chmod +x "$@"
