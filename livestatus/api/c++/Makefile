# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

ifneq (DEBUG,)
  CXXFLAGS += -g -DDEBUG
  LDFLAGS += -g
endif

all: demo

demo.o: demo.cc Livestatus.h
	$(CXX) $(CXXFLAGS) -c -o $@ $<

Livestatus.o: Livestatus.cc Livestatus.h
	$(CXX) $(CXXFLAGS) -c -o $@ $<

demo: demo.o Livestatus.o
	$(CXX) $(CXXFLAGS) $(LDFLAGS) -o $@ $^

clean:
	$(RM) demo.o demo Livetatus.o
