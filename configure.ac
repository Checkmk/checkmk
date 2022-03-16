# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Process this file with autoconf to produce a configure script.

AC_PREREQ(2.61)
AC_INIT([MK Livestatus], [2.1.0b3], [mk@mathias-kettner.de])
AM_INIT_AUTOMAKE([-Wall -Wno-portability foreign subdir-objects])
AM_EXTRA_RECURSIVE_TARGETS([all-packaging])
AC_CONFIG_MACRO_DIR([m4])
AC_CONFIG_SRCDIR([config.h.in])
AC_CONFIG_HEADER([config.h])
AC_DEFINE_UNQUOTED([BUILD_DATE], ["`date -R`"], [build date])
AC_DEFINE_UNQUOTED([BUILD_HOSTNAME], ["`uname -n`"], [name of the build host])
AC_REQUIRE_AUX_FILE([compile])
AC_REQUIRE_AUX_FILE([config.guess])
AC_REQUIRE_AUX_FILE([config.sub])

# Checks for programs.
AC_PROG_CC([clang-13 gcc-11 clang-12 gcc-10 clang-11 clang-10 gcc-9 clang-9 clang-8 gcc-8 clang-7 gcc-7 clang-6.0 clang-5.0 gcc clang])
AC_PROG_CC_C99([], [])
if test "x$ac_cv_prog_cc_c99" = xno; then
  AC_MSG_ERROR([Need a C99-compliant C compiler])
fi
AC_PROG_CXX([clang++-13 g++-11 clang++-12 g++-10 clang++-11 clang++-10 g++-9 clang++-9 clang++-8 g++-8 clang++-7 g++-7 clang++-6.0 clang++-5.0 g++ clang++])
AC_DEFINE_UNQUOTED([BUILD_CXX], ["`$CXX --version | head -n1`"], [C++ compiler])
AX_CXX_COMPILE_STDCXX([17], [noext], [mandatory])
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
AC_CHECK_HEADERS([arpa/inet.h fcntl.h limits.h netdb.h netinet/in.h stdint.h stdlib.h string.h strings.h sys/socket.h sys/time.h syslog.h unistd.h])

# Checks for C++ features
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
AC_CHECK_FUNCS([memmove select socket strerror strtoul])

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
