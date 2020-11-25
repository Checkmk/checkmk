PIPENV := ../../scripts/run-pipenv
THREE_TO_TWO := $(PIPENV) run 3to2

# New plugins are expected to all have a .py extension. This will discover them
# automatically.  Old plugins without extension are explicitly whitelistet here
# to be found.
PYTHON3_PLUGINS := $(wildcard *[^_2].py)

.PHONY: all clean

all: $(addsuffix _2.py,$(PYTHON3_PLUGINS:.py=))

clean:
	$(RM) *_2.py

%_2.py: %.py
	cat "$<" | gawk -v text="# Do not test generated 2.x files\n# yapf: disable\n# type: ignore" '!/^#/ && !p {print text; p=1} 1' > "$@"
	sed -i 's/#!\/usr\/bin\/env python3/#!\/usr\/bin\/env python2/g' "$@"
	$(THREE_TO_TWO) --nofix=str --nobackups --write "$@" >/dev/null
	chmod +x "$@"
