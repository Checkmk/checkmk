#include "DynamicHostFileColumn.h"
#include <filesystem>
#include <stdexcept>
#include <utility>
#include "FileSystemHelper.h"
#include "HostFileColumn.h"
class Row;

DynamicHostFileColumn::DynamicHostFileColumn(
    const std::string &name, const std::string &description,
    Column::Offsets offsets, std::function<std::filesystem::path()> basepath,
    std::function<std::optional<std::filesystem::path>(
        const Column &, const Row &, const std::string &)>
        filepath)
    : DynamicColumn(name, description, std::move(offsets))
    , _basepath{std::move(basepath)}
    , _filepath{std::move(filepath)} {}

[[nodiscard]] std::filesystem::path DynamicHostFileColumn::basepath() const {
    // This delays the call to mc to after it is constructed.
    return _basepath();
}

std::unique_ptr<Column> DynamicHostFileColumn::createColumn(
    const std::string &name, const std::string &arguments) {
    // Arguments contains a path relative to basepath and possibly escaped.
    if (arguments.empty()) {
        throw std::runtime_error("invalid arguments for column '" + _name +
                                 "': missing file name");
    }
    const std::filesystem::path f{mk::unescape_filename(arguments)};
    if (!mk::path_contains(basepath(), basepath() / f)) {
        // Prevent malicious attempts to read files as root with
        // "/etc/shadow" (abs paths are not stacked) or
        // "../../../../etc/shadow".
        throw std::runtime_error("invalid arguments for column '" + _name +
                                 "': '" + f.string() + "' not in '" +
                                 basepath().string() + "'");
    }
    return std::make_unique<HostFileColumn>(
        name, _description, _offsets, _basepath,
        [=](const Column &col, const Row &row) {
            return _filepath(col, row, f);
        });
}
