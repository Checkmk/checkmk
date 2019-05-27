# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

# TODO(sp) We should really use autotools here...
ifneq ($(shell which g++-9 2>/dev/null),)
        CXX := g++-9 -std=c++17
else ifneq ($(shell which clang++-8 2>/dev/null),)
        CXX := clang++-8 -std=c++17
else ifneq ($(shell which g++-8 2>/dev/null),)
        CXX := g++-8 -std=c++17
else ifneq ($(shell which clang++-7 2>/dev/null),)
        CXX := clang++-7 -std=c++17
else ifneq ($(shell which g++-7 2>/dev/null),)
        CXX := g++-7 -std=c++17
else ifneq ($(shell which clang++-6.0 2>/dev/null),)
        CXX := clang++-6.0 -std=c++17
else ifneq ($(shell which clang++-5.0 2>/dev/null),)
        CXX := clang++-5.0 -std=c++17
else ifneq ($(shell which g++ 2>/dev/null),)
        CXX := g++ -std=c++17
else
        CXX := clang++ -std=c++17
endif

CXXFLAGS    := -g -O3 -Wall -Wextra
LDFLAGS     := -static-libstdc++

.PHONY: all clean

all: $(EXECUTABLES)

clean:
	$(RM) $(EXECUTABLES)
