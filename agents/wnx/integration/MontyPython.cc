// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

// A dummy plugin for testing the execution of binary plugins.
#include <iostream>

int main(int, char **) {
    std::cout << "<<<monty_python>>>" << std::endl;
    std::cout << "Monty Python's Flying Circus" << std::endl;
    return 0;
}
