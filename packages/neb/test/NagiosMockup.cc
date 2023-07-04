// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// NOLINTNEXTLINE(bugprone-suspicious-include)
#include "DummyNagios.cc"

extern "C" {
int nebmodule_init(int flags, char *args, void *handle);
int nebmodule_deinit(int flags, int reason);
}

int main() {
    nebmodule_init(0, nullptr, nullptr);
    nebmodule_deinit(0, 0);
    return 0;
}
