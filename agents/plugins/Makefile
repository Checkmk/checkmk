PIPENV3 := ../../scripts/run-pipenv 3
3TO2 := $(PIPENV3) run 3to2

# New plugins are expected to all have a .py extension. This will discover them
# automatically.  Old plugins without extension are explicitly whitelistet here
# to be found.
PYTHON3_PLUGINS := $(wildcard *.py) \
    apache_status \
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

.PHONY: all clean

all: $(addsuffix .py2,$(PYTHON3_PLUGINS:.py=))

clean:
	$(RM) *.py2

%.py: %
	cp "$<" "$@"

%.py2: %.py
	cat "$<" | gawk -v text="# Do not test generated 2.6 files\n# type: ignore" '!/^#/ && !p {print text; p=1} 1' > "$@"
	$(3TO2) --nofix=str --nobackups --write "$@" >/dev/null
