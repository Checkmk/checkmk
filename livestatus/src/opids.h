// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2015             mk@mathias-kettner.de |
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

#ifndef opids_h
#define opids_h

#include "config.h"

#define OP_INVALID       0
#define OP_EQUAL         1 // =
#define OP_REGEX         2 // ~
#define OP_EQUAL_ICASE   3 // =~
#define OP_REGEX_ICASE   4 // ~~
#define OP_GREATER       5 // >
#define OP_LESS          6 // <

extern const char *op_names_plus_8[];

// Note: The operators !=, <= and >= are parsed into ! =, ! > and ! <.
// The negation is represented by negating the value of the operator.
// Example >= is represented as -6 (- OP_LESS)

#endif // opids_h

