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

void print_perf_counter(int counter_id, const char *counter_name) {
    PerfCounterObject counterObject(counter_id);

    if (!counterObject.isEmpty()) {
        printf("<<<%s:%d>>>\n", counter_name, counter_id);
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

void print_perf_counter(const char *counter_pattern) {
    for (auto counter : PerfCounterObject::counter_list("CurrentLanguage")) {
        if (globmatch(counter_pattern, counter.second.c_str())) {
            try {
                print_perf_counter(counter.first, counter.second.c_str());
            } catch (const std::exception &e) {
                printf("Failed to read %s:%d: %s\n", counter.second.c_str(),
                       counter.first, e.what());
            }
        }
    }
    for (auto counter : PerfCounterObject::counter_list("009")) {
        if (globmatch(counter_pattern, counter.second.c_str())) {
            try {
                print_perf_counter(counter.first, counter.second.c_str());
            } catch (const std::exception &e) {
                printf("Failed to read %s:%d: %s\n", counter.second.c_str(),
                       counter.first, e.what());
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
        print_perf_counter(argv[1]);

        return 0;
    } catch (const std::exception &e) {
        printf("Failed: %s\n", e.what());
    }

    return 0;
}
