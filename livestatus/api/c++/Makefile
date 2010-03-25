ifneq (DEBUG,)
  CXXFLAGS += -g -DDEBUG
  LDFLAGS += -g
endif

all: demo

demo.o: demo.cc Livestatus.h
	g++ $(CXXFLAGS) -c -o $@ $<

Livestatus.o: Livestatus.cc Livestatus.h
	g++ $(CXXFLAGS) -c -o $@ $<

demo: demo.o Livestatus.o
	g++ $(CXXFLAGS) $(LDFLAGS) -o $@ $^

clean:
	rm -f demo.o demo Livetatus.o
