// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/strutil.h"

/* similar to next_field() but takes one character as delimiter */
char *next_token(char **c, char delim) {
    char *begin = *c;
    if (*begin == 0) {
        *c = begin;
        return nullptr;
    }

    char *end = begin;
    while (*end != 0 && *end != delim) {
        end++;
    }
    if (*end != 0) {
        *end = 0;
        *c = end + 1;
    } else {
        *c = end;
    }
    return begin;
}
