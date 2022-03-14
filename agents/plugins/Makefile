PIPENV := ../../scripts/run-pipenv
THREE_TO_TWO := $(PIPENV) run 3to2

# New plugins are expected to all have a .py extension. This will discover them
# automatically.  Old plugins without extension are explicitly whitelistet here
# to be found.
PYTHON3_PLUGINS := $(wildcard *[^_2].py)
PYTHON2_PLUGINS := $(addsuffix _2.py,$(PYTHON3_PLUGINS:.py=))

.PHONY: all clean

all: $(PYTHON2_PLUGINS)

clean:
	$(RM) *_2.py *.checksum

# During creation of the source packages we update the Checkmk version using
# "make setversion" from the base directory. This updates the Checkmk version
# of the agent .py files and also the mtime of the .py files which results in
# "make" rebuild all _2.py files even if they didn't change compared to the
# last time. Since we want to optimize the time of the source package build, we
# introduce this to use the source file hash to decide whether or not to update
# the _2.py files. Not ideal, but works. Let me know if you have something
# better.
%.checksum: %
	md5sum $< | cmp -s $@ -; if test $$? -ne 0; then md5sum $< > $@; fi

.SECONDARY:

%_2.py: %.py.checksum
	cat "$(<:.checksum=)" | gawk -v text="# Do not test generated 2.x files\n# yapf: disable\n# type: ignore" '!/^#/ && !p {print text; p=1} 1' > "$@"
	sed -i 's/#!\/usr\/bin\/env python3/#!\/usr\/bin\/env python2/g' "$@"
	$(THREE_TO_TWO) --nofix=str --nobackups --write "$@" >/dev/null
	chmod +x "$@"
