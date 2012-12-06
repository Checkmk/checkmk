all: mkevent mkeventd_open514

mkevent: mkevent.c
	diet gcc -O2 -s -o mkevent mkevent.c || \
	gcc -O2 -o mkevent mkevent.c

mkeventd_open514: mkeventd_open514.c
	gcc -O2 -o $@ $<

clean:
	rm -f mkevent mkeventd_open514
