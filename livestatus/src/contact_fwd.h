// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef contact_fwd_h
#define contact_fwd_h

#if defined(CMC)
class Contact;
using contact = Contact;
#elif defined(NAGIOS4)
typedef struct contact contact;
#else
using contact = struct contact_struct;
#endif

#endif  // contact_fwd_h
