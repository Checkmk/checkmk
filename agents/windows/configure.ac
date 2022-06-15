#                                               -*- Autoconf -*-
# Process this file with autoconf to produce a configure script.

AC_PREREQ([2.69])
AC_INIT([Check_MK Windows Agent], [1.6.0p30], [feedback@checkmk.com])
AM_INIT_AUTOMAKE([foreign subdir-objects])
AC_CONFIG_COMMANDS([check_chroot], \
                   [[[ -z $CHROOT_NAME ]] && \
                   echo "Not allowed outside chroot. Please call './make-agent' instead." && \
                   exit 1])
AC_CONFIG_SRCDIR([config.h.in])
AC_CONFIG_HEADER([config.h])

AC_EXEEXT
AC_OBJEXT

AC_ARG_VAR([WINDRES], [Binary executable for manipulating Windows resources])

# Checks for programs.
AC_PROG_CXX
AC_CHECK_PROG([WINDRES], @WINDRES@)
AC_CHECK_TOOL([STRIP], @STRIP@)
AC_PROG_INSTALL
AC_PROG_LN_S
AC_PROG_MAKE_SET
AC_PROG_RANLIB
# Checks for header files.
AC_CHECK_HEADERS([inttypes.h limits.h locale.h stdint.h sys/time.h unistd.h])

# Checks for typedefs, structures, and compiler characteristics.
AC_CHECK_HEADER_STDBOOL
AC_C_INLINE
AC_TYPE_INT64_T
AC_C_RESTRICT
AC_TYPE_SIZE_T
AC_TYPE_UINT16_T
AC_TYPE_UINT32_T
AC_TYPE_UINT64_T

# Checks for library functions.
AC_FUNC_ERROR_AT_LINE
AC_FUNC_MKTIME
AC_CHECK_FUNCS([gethostname gettimeofday localtime_r memmove memset select setlocale socket strcasecmp strchr strcspn strdup strerror strrchr strtol strtoul strtoull])

AC_CONFIG_FILES([Makefile])

AC_SUBST([MT], ['mt${EXEEXT}'])

AC_OUTPUT
