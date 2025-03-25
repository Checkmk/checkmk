// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef test_utilities_h
#define test_utilities_h

#include <functional>
#include <string>
#include <vector>

#include "livestatus/Interface.h"
#include "neb/nagios.h"

// Nagios and const-correctness: A Tale of Two Worlds...
char *cc(const char *str);

class CustomVariables {
public:
    explicit CustomVariables(Attributes attrs);
    customvariablesmember *start();

private:
    Attributes attrs_;  // to keep sthe strings alive
    std::vector<customvariablesmember> cvms_;
};

class TestHost : public host {
public:
    explicit TestHost(const Attributes &cust_vars);

private:
    CustomVariables cust_vars_;
};

class TestService : public service {
public:
    TestService(host *h, const Attributes &cust_vars);

private:
    CustomVariables cust_vars_;
};

#endif  // test_utilities_h
