// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// Copyright by Mathias Kettner and Mathias Kettner GmbH.  All rights reserved.
//
// Check_MK is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.
//
// Check_MK is  distributed in the hope that it will be useful, but
// WITHOUT ANY WARRANTY;  without even the implied warranty of
// MERCHANTABILITY  or  FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU General Public License for more details.
//
// You should have  received  a copy of the  GNU  General Public
// License along with Check_MK.  If  not, email to mk@mathias-kettner.de
// or write to the postal address provided at www.mathias-kettner.de

#include <unistd.h>
#include <stdio.h>
#include <sys/stat.h>

#include "mk_inventory.h"

#ifdef CMC
#include <Config.h>
#define MK_INVENTORY_PATH g_config->_mk_inventory_path
#else
extern char g_mk_inventory_path[];
#define MK_INVENTORY_PATH g_mk_inventory_path
#endif

int mk_inventory_last(const char *host)
{
    char path[4096];
    snprintf(path, sizeof(path), "%s/%s", MK_INVENTORY_PATH, host);
    struct stat st;
    if (0 != stat(path, &st))
        return 0;
    else
        return st.st_mtime;
}

int mk_inventory_last_of_all()
{
    // Check_MK Inventory touches the file ".last" after each inventory
    return mk_inventory_last(".last");
}
