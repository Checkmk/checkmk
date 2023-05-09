// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef nagios_h
#define nagios_h

#include "config.h"  // IWYU pragma: keep

// IWYU pragma: begin_exports
#ifdef CMC
#include "cmc.h"
#else
#define NSCORE
#ifdef NAGIOS4
#include "nagios4/broker.h"
#include "nagios4/common.h"
#include "nagios4/downtime.h"
#include "nagios4/logging.h"
#include "nagios4/macros.h"
#include "nagios4/nagios.h"
#include "nagios4/nebcallbacks.h"
#include "nagios4/neberrors.h"
#include "nagios4/nebmodules.h"
#include "nagios4/nebstructs.h"
#include "nagios4/objects.h"
#else
#include "nagios/broker.h"
#include "nagios/common.h"
#include "nagios/downtime.h"
#include "nagios/macros.h"
#include "nagios/nagios.h"
#include "nagios/nebcallbacks.h"
#include "nagios/neberrors.h"
#include "nagios/nebmodules.h"
#include "nagios/nebstructs.h"
#include "nagios/objects.h"
#endif  // NAGIOS4
#endif  // CMC
// IWYU pragma: end_exports
#endif  // nagios_h
