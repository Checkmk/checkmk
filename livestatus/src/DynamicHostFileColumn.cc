#include "DynamicHostFileColumn.h"
#include <filesystem>
#include <stdexcept>
#include <utility>
#include "Column.h"
#include "FileSystemHelper.h"
#include "HostFileColumn2.h"

DynamicHostFileColumn::DynamicHostFileColumn(
    const std::string &name, const std::string &description,
    int indirect_offset, int extra_offset, int extra_extra_offset,
    std::function<std::filesystem::path()> basepath)
    : DynamicColumn(name, description, indirect_offset, extra_offset,
                    extra_extra_offset)
    , basepath_{std::move(basepath)} {}

[[nodiscard]] std::filesystem::path DynamicHostFileColumn::basepath() const {
    // This delays the call to mc to after it is constructed.
    return basepath_();
}

std::unique_ptr<Column> DynamicHostFileColumn::createColumn(
    const std::string &name, const std::string &arguments) {
    // Arguments contains a path relative to basepath.
    const std::filesystem::path filepath{arguments};
    if (arguments.empty()) {
        throw std::runtime_error("invalid arguments for column '" + _name +
                                 "': missing file name");
    }
    if (!mk::path_contains(basepath(), basepath() / filepath)) {
        // Prevent malicious attempts to read files as root with
        // "/etc/shadow" (abs paths are not stacked) or
        // "../../../../etc/shadow".
        throw std::runtime_error("invalid arguments for column '" + _name +
                                 "': '" + filepath.string() + "' not in '" +
                                 basepath().string() + "'");
    }
    return std::make_unique<HostFileColumn2>(name, _description,
                                             _indirect_offset, _extra_offset,
                                             -1, 0, basepath(), filepath);
}
