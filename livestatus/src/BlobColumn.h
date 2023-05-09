// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef BlobColumn_h
#define BlobColumn_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <filesystem>
#include <functional>
#include <iterator>
#include <memory>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

#include "Column.h"
#include "Filter.h"
#include "Logger.h"
#include "Row.h"
#include "contact_fwd.h"
#include "opids.h"
class Aggregator;
class RowRenderer;

namespace detail {
class BlobColumn : public Column {
public:
    class Constant;
    class Reference;
    using Column::Column;

    [[nodiscard]] ColumnType type() const override { return ColumnType::blob; }

    void output(Row row, RowRenderer &r, const contact *auth_user,
                std::chrono::seconds timezone_offset) const override;

    [[nodiscard]] std::unique_ptr<Filter> createFilter(
        Filter::Kind kind, RelationalOperator relOp,
        const std::string &value) const override;

    [[nodiscard]] std::unique_ptr<Aggregator> createAggregator(
        AggregationFactory factory) const override;

    [[nodiscard]] virtual std::unique_ptr<std::vector<char>> getValue(
        Row row) const = 0;
};
}  // namespace detail

template <class T>
class BlobColumn : public ::detail::BlobColumn {
public:
    using ::detail::BlobColumn::Constant;
    using ::detail::BlobColumn::Reference;
    struct File;
    BlobColumn(const std::string &name, const std::string &description,
               const ColumnOffsets &offsets,
               std::function<std::vector<char>(const T &)> f)
        : detail::BlobColumn{name, description, offsets}
        , get_value_{std::move(f)} {}
    ~BlobColumn() override = default;
    [[nodiscard]] std::unique_ptr<std::vector<char>> getValue(
        Row row) const override {
        const T *data = columnData<T>(row);
        return std::make_unique<std::vector<char>>(
            data == nullptr ? std::vector<char>{} : get_value_(*data));
    }

private:
    const std::function<std::vector<char>(const T &)> get_value_;
};

class detail::BlobColumn::Constant : public ::detail::BlobColumn {
public:
    Constant(std::string name, std::string description, std::vector<char> v)
        : detail::BlobColumn(std::move(name), std::move(description), {})
        , v{std::move(v)} {};
    ~Constant() override = default;
    [[nodiscard]] std::unique_ptr<std::vector<char>> getValue(
        Row /*row*/) const override {
        return std::make_unique<std::vector<char>>(v);
    }

private:
    const std::vector<char> v;
};

class detail::BlobColumn::Reference : public ::detail::BlobColumn {
public:
    Reference(std::string name, std::string description,
              const std::vector<char> &v)
        : BlobColumn(std::move(name), std::move(description), {}), v{v} {};
    ~Reference() override = default;
    [[nodiscard]] std::unique_ptr<std::vector<char>> getValue(
        Row /*row*/) const override {
        return std::make_unique<std::vector<char>>(v);
    }

private:
    const std::vector<char> &v;
};

template <class T>
struct BlobColumn<T>::File : BlobColumn {
    File(const std::string &name, const std::string &description,
         const ColumnOffsets &offsets,
         const std::function<std::filesystem::path()> &basepath,
         std::function<std::filesystem::path(const T &)> filepath);
    ~File() override = default;
};

namespace detail {
template <class T>
class FileImpl {
public:
    FileImpl(std::function<std::filesystem::path()> basepath,
             std::function<std::filesystem::path(const T &)> filepath)
        : _basepath{std::move(basepath)}
        , _filepath{std::move(filepath)}
        , _logger{"cmk.livestatus"} {}
    std::vector<char> operator()(const T & /*data*/) const;
    Logger *logger() const { return &_logger; }

private:
    const std::function<std::filesystem::path()> _basepath;
    const std::function<std::filesystem::path(const T &)> _filepath;
    mutable ThreadNameLogger _logger;
};
}  // namespace detail

template <class T>
std::vector<char> detail::FileImpl<T>::operator()(const T &data) const {
    auto path = _basepath();
    if (!std::filesystem::exists(path)) {
        // The basepath is not configured.
        return {};
    }
    auto filepath = _filepath(data);
    if (!filepath.empty()) {
        path /= filepath;
    }
    if (!std::filesystem::is_regular_file(path)) {
        Debug(logger()) << path << " is not a regular file";
        return {};
    }
    auto file_size = std::filesystem::file_size(path);
    std::ifstream ifs;
    ifs.open(path, std::ifstream::in | std::ifstream::binary);
    if (!ifs.is_open()) {
        generic_error ge("cannot open " + path.string());
        Warning(logger()) << ge;
        return {};
    }
    using iterator = std::istreambuf_iterator<char>;
    auto buffer = std::vector<char>(file_size);
    buffer.assign(iterator{ifs}, iterator{});
    if (buffer.size() != file_size) {
        Warning(logger()) << "premature EOF reading " << path;
        return {};
    }
    return buffer;
}

template <class T>
BlobColumn<T>::File::File(
    const std::string &name, const std::string &description,
    const ColumnOffsets &offsets,
    const std::function<std::filesystem::path()> &basepath,
    std::function<std::filesystem::path(const T &)> filepath)
    : BlobColumn{name, description, offsets,
                 detail::FileImpl{basepath, std::move(filepath)}} {}

#endif  // BlobColumn_h
