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

#ifndef HostlistStateColumn_h
#define HostlistStateColumn_h

#include "config.h"

#include "IntColumn.h"
#include "ServicelistStateColumn.h"
#include "nagios.h"

#define HLSC_NUM_SVC               SLSC_NUM
#define HLSC_NUM_SVC_PENDING       SLSC_NUM_PENDING
#define HLSC_NUM_SVC_OK            SLSC_NUM_OK
#define HLSC_NUM_SVC_WARN          SLSC_NUM_WARN
#define HLSC_NUM_SVC_CRIT          SLSC_NUM_CRIT
#define HLSC_NUM_SVC_UNKNOWN       SLSC_NUM_UNKNOWN
#define HLSC_WORST_SVC_STATE       SLSC_WORST_STATE
#define HLSC_NUM_SVC_HARD_OK       SLSC_NUM_HARD_OK
#define HLSC_NUM_SVC_HARD_WARN     SLSC_NUM_HARD_WARN
#define HLSC_NUM_SVC_HARD_CRIT     SLSC_NUM_HARD_CRIT
#define HLSC_NUM_SVC_HARD_UNKNOWN  SLSC_NUM_HARD_UNKNOWN
#define HLSC_WORST_SVC_HARD_STATE  SLSC_WORST_HARD_STATE

#define HLSC_NUM_HST_UP       10
#define HLSC_NUM_HST_DOWN     11
#define HLSC_NUM_HST_UNREACH  12
#define HLSC_NUM_HST_PENDING  13
#define HLSC_NUM_HST          -11
#define HLSC_WORST_HST_STATE  -12


class HostlistStateColumn : public IntColumn
{
    int _offset;
    int _logictype;

public:
    HostlistStateColumn(string name, string description, int logictype, int offset, int indirect_offset)
        : IntColumn(name, description, indirect_offset), _offset(offset), _logictype(logictype) {}
    int32_t getValue(void *data, Query *);
    hostsmember *getMembers(void *data);
};


#endif // HostlistStateColumn_h

