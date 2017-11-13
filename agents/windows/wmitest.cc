#include <algorithm>
#include <string>
#include "WinApi.h"
#include "stringutil.h"
#include "wmiHelper.h"

namespace {
WinApi winapi;
}

void print_usage(const char *exe_name) {
    printf(
        "Usage: %s action [action specific parameters]"
        "\n\ttree                    - print the whole wmi namespace tree"
        "\n\tcsv <namespace> <class> - print the whole class table in csv "
        "format",
        exe_name);
}

void print_namespace(const std::wstring &path, int depth = 0) {
    wmi::Helper helper(winapi, path.c_str());

    std::string offset = std::string(depth * 2, ' ');
    {
        wmi::Result result = helper.query(L"SELECT name FROM __Namespace");
        bool more = result.valid();
        while (more) {
            std::wstring name = result.get<std::wstring>(L"name");
            printf("%s%ls\n", offset.c_str(), name.c_str());
            try {
                print_namespace(path + L"\\" + name, depth + 1);
            } catch (const std::exception &e) {
                printf("-- failed: %s\n", e.what());
            }

            more = result.next();
        }
    }
    {
        wmi::Result result = helper.query(L"SELECT * FROM meta_class");
        bool more = result.valid();
        while (more) {
            std::wstring name = result.get<std::wstring>(L"__CLASS");
            printf("%s> %ls\n", offset.c_str(), name.c_str());
            more = result.next();
        }
    }
}

void print_table(const std::string &ns, const std::string &pattern) {
    wmi::Helper helper(winapi, to_utf16(ns.c_str(), winapi).c_str());

    wmi::Result result = helper.query(L"SELECT * FROM meta_class");
    bool more = result.valid();
    if (!more) {
        printf("Invalid result for meta_class\n");
    }
    while (more) {
        std::wstring name = result.get<std::wstring>(L"__CLASS");
        try {
            if (globmatch(pattern.c_str(), to_utf8(name.c_str()).c_str())) {
                printf("<<<%ls>>>\n", name.c_str());
                wmi::Result sub_result = helper.query(
                    (std::wstring(L"SELECT * FROM ") + name).c_str());
                bool first = true;
                bool sub_more = sub_result.valid();
                if (!sub_more) {
                    printf("Invalid or empty result\n");
                }
                while (sub_more) {
                    if (first) {
                        // print header
                        printf("%ls\n", join(sub_result.names(), L",").c_str());
                        first = false;
                    }
                    std::vector<std::wstring> values = sub_result.names();
                    // resolve all table keys to their value on this row.
                    std::transform(
                        values.begin(), values.end(), values.begin(),
                        [&sub_result](const std::wstring &name) {
                            return sub_result.get<std::wstring>(name.c_str());
                        });
                    printf("%ls\n", join(values, L",").c_str());

                    sub_more = sub_result.next();
                }
            }
        } catch (const std::exception &e) {
            printf("Exception: %s\n", e.what());
        }
        more = result.next();
    }
}

int main(int argc, char **argv) {
    if (argc < 2) {
        print_usage(argv[0]);
        return 1;
    }

    try {
        if (strcmp(argv[1], "tree") == 0) {
            if (argc < 3) {
                print_namespace(L"Root");
            } else {
                print_namespace(to_utf16(argv[2], winapi).c_str());
            }
        }

        if (strcmp(argv[1], "csv") == 0) {
            if (argc < 4) {
                print_usage(argv[0]);
                return 1;
            }
            print_table(argv[2], argv[3]);
        }

        return 0;
    } catch (const std::exception &e) {
        printf("Failed: %s\n", e.what());
    }
}
