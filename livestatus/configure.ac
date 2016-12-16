#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
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

#                                               -*- Autoconf -*-
# Process this file with autoconf to produce a configure script.

AC_PREREQ(2.61)
AC_INIT([MK Livestatus], [1.4.0i3p1], [mk@mathias-kettner.de])
AM_INIT_AUTOMAKE([-Wall foreign])
AC_CONFIG_MACRO_DIR([m4])
AC_CONFIG_SRCDIR([config.h.in])
AC_CONFIG_HEADER([config.h])
AC_REQUIRE_AUX_FILE([compile])
AC_REQUIRE_AUX_FILE([config.guess])
AC_REQUIRE_AUX_FILE([config.sub])

# Checks for programs.
AC_PROG_CC([gcc-6 gcc-5 clang-3.9 clang-3.8 clang-3.7 clang-3.6 clang-3.5 gcc-4.9 gcc clang])
AC_PROG_CC_C99([], [])
if test "x$ac_cv_prog_cc_c99" = xno; then
  AC_MSG_ERROR([Need a C99-compliant C compiler])
fi
AC_PROG_CXX([g++-6 g++-5 clang++-3.9 clang++-3.8 clang++-3.7 clang++-3.6 clang++-3.5 g++-4.9 g++ clang++])
AX_CXX_COMPILE_STDCXX([14], [noext], [mandatory])
AC_PROG_RANLIB
# automake 1.12 seems to require this, but automake 1.11 doesn't recognize it. :-P
m4_ifdef([AM_PROG_AR], [AM_PROG_AR])

# Checks for libraries.
AC_CHECK_LIB(socket, socket)
AC_CHECK_LIB(socket, connect)
AC_CHECK_LIB(socket, shutdown)

# Checks for header files.
AC_HEADER_DIRENT
AC_HEADER_STDC
AC_HEADER_SYS_WAIT
AC_CHECK_HEADERS([arpa/inet.h fcntl.h limits.h netdb.h netinet/in.h stdint.h stdlib.h string.h strings.h sys/socket.h sys/time.h sys/timeb.h syslog.h unistd.h])

# Checks for C++ features
AC_LANG_PUSH([C++])

AC_MSG_CHECKING([whether C++14 headers are supported by default])
AC_COMPILE_IFELSE(
    [AC_LANG_PROGRAM([#include <shared_mutex>], [])],
    [AC_MSG_RESULT([yes])],
    [AC_MSG_RESULT([no])
     CXX="$CXX -stdlib=libc++"
     CXXCPP="$CXXCPP -stdlib=libc++"
     AC_MSG_CHECKING([whether C++14 headers are supported with -stdlib=libc++])
     AC_COMPILE_IFELSE(
         [AC_LANG_PROGRAM([#include <shared_mutex>], [])],
         [AC_MSG_RESULT([yes])],
         [AC_MSG_RESULT([no])
          AC_MSG_ERROR([C++ headers are too old. Please install a newer g++/clang/libc++-dev package.])])])

AC_LANG_POP([C++])

# Checks for typedefs, structures, and compiler characteristics.
AC_HEADER_STDBOOL
AC_C_CONST
AC_C_INLINE
AC_TYPE_INT32_T
AC_TYPE_INT64_T
AC_TYPE_SIZE_T
AC_TYPE_SSIZE_T
AC_HEADER_TIME
AC_TYPE_UINT32_T
AC_TYPE_UINT64_T

# Checks for library functions.
AC_FUNC_MALLOC
AC_FUNC_REALLOC
AC_FUNC_SELECT_ARGTYPES
AC_TYPE_SIGNAL
AC_FUNC_STAT
AC_CHECK_FUNCS([bzero gettimeofday memmove regcomp select socket strcasecmp strdup strerror strtoul])

AC_ARG_WITH(nagios4,AC_HELP_STRING([--with-nagios4],[enabled compilation for nagios 4]), [
    CPPFLAGS="${CFLAGS} -DNAGIOS4"
    nagios_headers=nagios4
    ],
    nagios_headers=nagios)
AC_SUBST(nagios_headers)

AC_CONFIG_FILES([Makefile
                 src/Makefile])
AC_OUTPUT
