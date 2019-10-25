#include "CrashReport.h"
#include <regex>
#include <utility>
#include <vector>

CrashReport::CrashReport(std::string id, std::string component)
    : _id(std::move(id)), _component(std::move(component)) {}

std::string CrashReport::id() const { return _id; }

std::string CrashReport::component() const { return _component; }

// TODO(ml): This would be cleaner with ranges.
void for_each_crash_report(
    const std::filesystem::path &base_path,
    const std::function<void(const CrashReport &)> &fun) {
    const std::regex uuid_pattern(
        R"(^\S{4}(?:\S{4}-){4}\S{12}$)",
        std::regex_constants::ECMAScript | std::regex_constants::icase);
    if (!std::filesystem::is_directory(base_path)) {
        return;
    }
    for (const auto &component_dir :
         std::filesystem::directory_iterator(base_path)) {
        if (!component_dir.is_directory()) {
            continue;
        }
        for (const auto &id_dir :
             std::filesystem::directory_iterator(component_dir)) {
            if (!(id_dir.is_directory() and
                  std::regex_search(id_dir.path().stem().string(),
                                    uuid_pattern))) {
                continue;
            }
            fun(CrashReport(id_dir.path().stem(), component_dir.path().stem()));
        }
    }
}
