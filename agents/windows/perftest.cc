// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#include "PerfCounter.h"
#include "stringutil.h"
#include "types.h"
#define __STDC_FORMAT_MACROS
#include <inttypes.h>

void print_usage(const char *exe_name) {
    printf(
        "Usage: %s pattern"
        "\n\t                    - print all performance counters that match "
        "the pattern",
        exe_name);
}

void print_perf_counter(int counter_id, const wchar_t *counter_name) {
    PerfCounterObject counterObject(counter_id);

    if (!counterObject.isEmpty()) {
        printf("<<<%ls:%d>>>\n", counter_name, counter_id);
        printf("index,type,\"%ls\"\n",
               join(counterObject.instanceNames(), L"\",\"").c_str());

        std::vector<PERF_INSTANCE_DEFINITION *> instances =
            counterObject.instances();

        // output counters
        for (const PerfCounter &counter : counterObject.counters()) {
            printf("%" PRIudword, counter.titleIndex());
            printf(",%s", counter.typeName().c_str());
            for (ULONGLONG value : counter.values(instances)) {
                printf(",%" PRIu64, value);
            }
            printf("\n");
        }
    }
}

void print_perf_counter(const wchar_t *counter_pattern) {
    for (auto obj : PerfCounterObject::object_list("CurrentLanguage")) {
        if (globmatch(counter_pattern, obj.second.c_str())) {
            try {
                print_perf_counter(obj.first, obj.second.c_str());
            } catch (const std::exception &e) {
                printf("Failed to read %ls:%lu: %s\n", obj.second.c_str(),
                       obj.first, e.what());
            }
        }
    }
    for (auto obj : PerfCounterObject::object_list("009")) {
        if (globmatch(counter_pattern, obj.second.c_str())) {
            try {
                print_perf_counter(obj.first, obj.second.c_str());
            } catch (const std::exception &e) {
                printf("Failed to read %ls:%lu: %s\n", obj.second.c_str(),
                       obj.first, e.what());
            }
        }
    }
}

int main(int argc, char **argv) {
    if (argc < 2) {
        print_usage(argv[0]);
        return 1;
    }

    try {
        if (strcmp(argv[1], "--list") == 0) {
            for (const auto &idx_name : PerfCounterObject::object_list("009")) {
                printf("%lu = %ls\n", idx_name.first, idx_name.second.c_str());
                PerfCounterObject obj(idx_name.first);
                for (const auto &counter : obj.counterNames()) {
                    printf("  -> %ls\n", counter.c_str());
                }
            }
        } else {
            print_perf_counter(to_utf16(argv[1]).c_str());
        }

        return 0;
    } catch (const std::exception &e) {
        printf("Failed: %s\n", e.what());
    }

    return 0;
}
