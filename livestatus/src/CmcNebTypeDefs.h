// Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef CmcNebTypeDefs_h
#define CmcNebTypeDefs_h
#ifdef CMC
#include "contact_fwd.h"
class Host;  // IWYU pragma: keep
using host = Host;
class Service;  // IWYU pragma: keep
using service = Service;
// IWYU pragma: no_include "ObjectGroup.h"
template <typename T>
class ObjectGroup;  // IWYU pragma: keep
using hostgroup = ObjectGroup<Host>;
using servicegroup = ObjectGroup<Service>;
#else
#include "nagios.h"
#endif

#endif  // CmcNebTypeDefs_h
