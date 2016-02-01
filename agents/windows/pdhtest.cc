#include "PerfCounterPdh.h"
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

void print_perf_counter(const wchar_t *counter_pattern) {
    PerfCounterQuery query;

    std::vector<std::pair<std::wstring, HCOUNTER>> counters;

    for (const std::wstring &object : query.enumerateObjects()) {
        std::wstring object_en = query.trans(object);
        if (globmatch(counter_pattern, object.c_str()) ||
            globmatch(counter_pattern, object_en.c_str())) {
            StringList counter_names, instance_names;
            std::tie(counter_names, instance_names) =
                query.enumerateObject(object.c_str());
            for (const std::wstring &counter_name : counter_names) {
                for (const std::wstring &instance_name : instance_names) {
                    std::wstring counter_path =
                        query.makePath(object, instance_name, counter_name);
                    std::wstring path_en = query.makePath(
                        object_en, instance_name, query.trans(counter_name));
                    counters.push_back(std::make_pair(
                        path_en, query.addCounter(counter_path)));
                }
            }
        }
    }

    query.execute();

    for (const auto &counter : counters) {
        std::wstring value = query.counterValue(counter.second);
        printf("%ls: %ls\n", counter.first.c_str(), value.c_str());
    }
}

int main(int argc, char **argv) {
    if (argc < 2) {
        print_usage(argv[0]);
        return 1;
    }

    try {
        print_perf_counter(to_utf16(argv[1]).c_str());

        return 0;
    } catch (const std::exception &e) {
        printf("Failed: %s\n", e.what());
    }

    return 0;
}
