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

#ifndef nagios_h
#define nagios_h

#include "config.h"

#ifdef CMC
#include "../cmc.h"
#else
    #define NSCORE
    #ifdef NAGIOS4
    #include "nagios4/objects.h"
    #include "nagios4/nagios.h"
    #include "nagios4/nebstructs.h"
    #include "nagios4/neberrors.h"
    #include "nagios4/broker.h"
    #include "nagios4/nebmodules.h"
    #include "nagios4/nebcallbacks.h"
    #else
    #include "nagios/objects.h"
    #include "nagios/nagios.h"
    #include "nagios/nebstructs.h"
    #include "nagios/neberrors.h"
    #include "nagios/broker.h"
    #include "nagios/nebmodules.h"
    #include "nagios/nebcallbacks.h"
    #endif // NAGIOS4
#endif // CMC
#endif // nagios_h

