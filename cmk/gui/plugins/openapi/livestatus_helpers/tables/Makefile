# Regenerate a table file
%.py: FORCE
	@echo "GET columns\nColumns: description name table type\nFilter: table = $(basename $@)" | \
		sudo -u heute -i lq | ./_create_table.py $(basename $@) > $@

FORCE:

all: $(wildcard [a-z]*.py)

# Show a list of all tables in LiveStatus
list:
	@echo "GET columns\nColumns: table" | \
		sudo -u heute -i lq | sort -u
