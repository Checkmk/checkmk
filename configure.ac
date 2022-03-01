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

# Process this file with autoconf to produce a configure script.

AC_PREREQ(2.61)
AC_INIT([MK Livestatus], [1.6.0p29], [mk@mathias-kettner.de])
AM_INIT_AUTOMAKE([-Wall -Wno-portability foreign])
AC_CONFIG_MACRO_DIR([m4])
AC_CONFIG_SRCDIR([config.h.in])
AC_CONFIG_HEADER([config.h])
AC_DEFINE_UNQUOTED([BUILD_DATE], ["`date -R`"], [build date])
AC_DEFINE_UNQUOTED([BUILD_HOSTNAME], ["`uname -n`"], [name of the build host])
AC_REQUIRE_AUX_FILE([compile])
AC_REQUIRE_AUX_FILE([config.guess])
AC_REQUIRE_AUX_FILE([config.sub])

# Old (pre-1.6.0) versions of librrd were not thread-safe, so one has to use the
# thread-safe variant librrd_th explicitly. This in itself is already tragic
# enough, but to make things worse, you can't write a compile-time check to
# distinguish these versions. :-/ So we default to the assumption that librrd is
# thread-safe (which is the case within OMD) and the user of e.g. a standalone
# version of Livestatus on an old system has to use the configure flag below.
# Not really nice, but we can't really do much about that.
AC_ARG_ENABLE([rrd-is-thread-safe],
    AS_HELP_STRING([--disable-rrd-is-thread-safe], [Use librrd_th instead of librrd]))
AS_IF([test "x$enable_rrd_is_thread_safe" != "xno"], [RRDLIB_TO_CHECK=rrd],
      [RRDLIB_TO_CHECK=rrd_th])

# Checks for programs.
AC_PROG_CC([gcc-10 clang-10 gcc-9 clang-9 clang-8 gcc-8 clang-7 gcc-7 clang-6.0 clang-5.0 gcc clang])
AC_PROG_CC_C99([], [])
if test "x$ac_cv_prog_cc_c99" = xno; then
  AC_MSG_ERROR([Need a C99-compliant C compiler])
fi
AC_PROG_CXX([g++-10 clang++-10 g++-9 clang++-9 clang++-8 g++-8 clang++-7 g++-7 clang++-6.0 clang++-5.0 g++ clang++])
AC_DEFINE_UNQUOTED([BUILD_CXX], ["`$CXX --version | head -n1`"], [C++ compiler])
AX_CXX_COMPILE_STDCXX([17], [noext], [mandatory])
AC_PROG_RANLIB
# automake 1.12 seems to require this, but automake 1.11 doesn't recognize it. :-P
m4_ifdef([AM_PROG_AR], [AM_PROG_AR])

# Checks for libraries.
AC_CHECK_LIB(socket, socket)
AC_CHECK_LIB(socket, connect)
AC_CHECK_LIB(socket, shutdown)

# Passing through the right RRD library is a bit tricky: We can't simply put
# -lrrd_th or -lrrd globally into LIBS. The problem is that our SUID programs
# icmpsender and icmpreceiver would be linked with that option, too, but because
# of security reasons the dynamic linker will ignore our LD_LIBRARY_PATH => no
# RRD library found or even the wrong one... :-/
RRDLIB=
old_LIBS=$LIBS
AC_SEARCH_LIBS([rrd_xport], [$RRDLIB_TO_CHECK],
    [test "$ac_cv_search_rrd_xport" = "none required" || RRDLIB="$ac_cv_search_rrd_xport"],
    [AC_MSG_ERROR([unable to find the rrd_xport function])])
LIBS=$old_LIBS
AC_SUBST(RRDLIB)

# Checks for header files.
AC_HEADER_DIRENT
AC_HEADER_STDC
AC_HEADER_SYS_WAIT
AC_CHECK_HEADERS([arpa/inet.h fcntl.h limits.h netdb.h netinet/in.h stdint.h stdlib.h string.h strings.h sys/socket.h sys/time.h sys/timeb.h syslog.h unistd.h])

# Checks for C++ features
AX_BOOST_BASE(,,AC_MSG_ERROR([Boost library not found or too old]))
AX_BOOST_ASIO
if test "x$ax_cv_boost_asio" = xno; then
    AC_MSG_ERROR([Boost::ASIO library not found])
fi

AC_LANG_PUSH([C++])

AC_MSG_CHECKING([whether C++17 headers are supported by default])
AC_COMPILE_IFELSE(
    [AC_LANG_PROGRAM([#include <optional>
#include <shared_mutex>], [std::shared_mutex sm])],
    [AC_MSG_RESULT([yes])],
    [AC_MSG_RESULT([no])
     CXX="$CXX -stdlib=libc++"
     CXXCPP="$CXXCPP -stdlib=libc++"
     AC_MSG_CHECKING([whether C++17 headers are supported with -stdlib=libc++])
     AC_COMPILE_IFELSE(
         [AC_LANG_PROGRAM([#include <optional>
#include <shared_mutex>], [std::shared_mutex sm])],
         [AC_MSG_RESULT([yes])],
         [AC_MSG_RESULT([no])
          AC_MSG_ERROR([C++ headers are too old. Please install a newer g++/clang/libc++-dev package.])])])

# RE2 stuff
AC_ARG_WITH([re2],
            [AS_HELP_STRING([--with-re2@<:@=ARG@:>@],
                            [use RE2 library from a standard location (ARG=yes),
                             from the specified location (ARG=<path>),
                             or disable it (ARG=no) @<:@ARG=no@:>@ ])],
            [AS_CASE([$withval],
                     [no],[want_re2="no";_AX_RE2_BASE_re2_path=""],
                     [yes],[want_re2="yes";_AX_RE2_BASE_re2_path=""],
                     [want_re2="yes";_AX_RE2_BASE_re2_path="$withval"])],
            [want_re2="no"])
RE2_CPPFLAGS=""
RE2_LDFLAGS=""
RE2_LIBS=""
AS_IF([test "x$want_re2" = "xyes"],
      [AS_IF([test "x$_AX_RE2_BASE_re2_path" != x],
             [RE2_CPPFLAGS="-I$_AX_RE2_BASE_re2_path/include"
              RE2_LDFLAGS="-L$_AX_RE2_BASE_re2_path/lib"])
       RE2_LIBS="-lre2"
       CPPFLAGS_SAVED=$CPPFLAGS
       CPPFLAGS="$CPPFLAGS $RE2_CPPFLAGS"
       AC_CHECK_HEADER([re2/re2.h], [], [AC_MSG_ERROR([could not find a working RE2 header])])
       AC_MSG_CHECKING([for RE2 library])
       LDFLAGS_SAVED=$LDFLAGS
       LDFLAGS="$LDFLAGS $RE2_LDFLAGS"
       LIBS_SAVED=$LIBS
       LIBS="$LIBS $RE2_LIBS -pthread"
       AC_LINK_IFELSE([AC_LANG_PROGRAM([[@%:@include <re2/re2.h>]],
                                       [[RE2::FullMatch("hello", "e")]])],
                      [AC_MSG_RESULT([yes])],
                      [AC_MSG_RESULT([no])
                       AC_MSG_ERROR([could not find a working RE2 library])])
       LIBS=$LIBS_SAVED
       LDFLAGS=$LDFLAGS_SAVED
       CPPFLAGS=$CPPFLAGS_SAVED
       AC_DEFINE([HAVE_RE2], [1], [Define to 1 if RE2 should be used.])])
AC_SUBST(RE2_CPPFLAGS)
AC_SUBST(RE2_LDFLAGS)
AC_SUBST(RE2_LIBS)

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
AC_FUNC_SELECT_ARGTYPES
AC_TYPE_SIGNAL
AC_FUNC_STAT
AC_CHECK_FUNCS([accept4 memmove select socket strerror strtoul])

AC_ARG_WITH(nagios4,AC_HELP_STRING([--with-nagios4],[enabled compilation for nagios 4]), [
    CPPFLAGS="${CFLAGS} -DNAGIOS4"
    nagios_headers=nagios4
    ],
    nagios_headers=nagios)
AC_SUBST(nagios_headers)

# Compiling or executing a std::regex can fail with a stack overflow, causing
# our Livestatus threads to die, see e.g. the related bug report
# https://gcc.gnu.org/bugzilla/show_bug.cgi?id=61582. A workaround for this is
# to limit the number of NFA states, but this must be done at compile-time. To
# be sure that the limit is defined before <regex> is included, we set it
# here. If the limit is reached during runtime, the regex library will throw a
# std::regex_error with a std::regex_constants::error_space code. This whole
# thing is a kind of a hack, but currently there seems to be no way around that,
# at least not until the libstdc++ uses heap allocated memory instead of the
# stack... :-/
#
# Some numbers for x86_64: At the point where we compile or execute a regex, we
# already use almost 12kB stack. For compilation of a regex, each level of
# recursion uses additional 112 bytes. For executing a regex, each level of
# recursion uses additional 384 bytes. Our current stack size for the Livestatus
# threads is 1MB, so we can handle roughly 2700 states. To be on the safe side,
# we leave some breathing room and use a slightly lower limit.
AC_DEFINE([_GLIBCXX_REGEX_STATE_LIMIT], [2500],
          [the maximum number of states the regex NFA can have])

AC_DEFINE([BOOST_SYSTEM_NO_DEPRECATED], [1], [we do not want any old stuff])

# GCC is a bit picky about redefinitions of built-in macros. Alas, "built-in"
# simply means "starts with double underscore", so we have to hack around that
# below. Note that clang is happy, even without the guard.
AH_VERBATIM([__STDC_WANT_LIB_EXT1__], [/* we want C11 library extensions  */
#ifndef __STDC_WANT_LIB_EXT1__
# define __STDC_WANT_LIB_EXT1__ 1
#endif])

# HACKING ALERT: automake can't really handle optional subdirectories, so we
# have to do this in a slightly hacky way by using M4's silent includes.
m4_sinclude([livestatus/config_files.m4])
m4_sinclude([enterprise/config_files.m4])
m4_sinclude([standalone/config_files.m4])

AC_OUTPUT
