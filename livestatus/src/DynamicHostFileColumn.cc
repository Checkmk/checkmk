#include "DynamicHostFileColumn.h"
#include <filesystem>
#include <stdexcept>
#include <utility>
#include "Column.h"
#include "FileSystemHelper.h"
#include "HostFileColumn.h"
class Row;

DynamicHostFileColumn::DynamicHostFileColumn(
    const std::string &name, const std::string &description,
    int indirect_offset, int extra_offset, int extra_extra_offset,
    std::function<std::filesystem::path()> basepath,
    std::function<std::optional<std::filesystem::path>(
        const Column &, const Row &, const std::string &)>
        filepath)
    : DynamicColumn(name, description, indirect_offset, extra_offset,
                    extra_extra_offset)
    , _basepath{std::move(basepath)}
    , _filepath{std::move(filepath)} {}

[[nodiscard]] std::filesystem::path DynamicHostFileColumn::basepath() const {
    // This delays the call to mc to after it is constructed.
    return _basepath();
}

std::unique_ptr<Column> DynamicHostFileColumn::createColumn(
    const std::string &name, const std::string &arguments) {
    // Arguments contains a path relative to basepath and possibly escaped.
    const std::filesystem::path filepath{mk::unescape_filename(arguments)};
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
    return std::make_unique<HostFileColumn>(
        name, _description, _indirect_offset, _extra_offset, -1, 0, _basepath,
        [&filepath, this](const Column &col, const Row &row) {
            return _filepath(col, row, filepath);
        });
}
