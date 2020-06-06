PIPENV3 := ../../scripts/run-pipenv 3
3TO2 := $(PIPENV3) run 3to2

.PHONY: all

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

PYTHON2_PLUGINS := $(addsuffix .py2,$(patsubst %.py,%,$(PYTHON3_PLUGINS)))

all: $(PYTHON2_PLUGINS)

%.py: %
	cp "$<" "$@"

%.py2: %.py
	mkdir -p "$(dir $@)"
	cp "$<" "$@"
	$(3TO2) -x str -n -w "$@" >/dev/null
