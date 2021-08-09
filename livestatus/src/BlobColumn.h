// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
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
#include "POSIXUtils.h"
#include "Row.h"
#include "contact_fwd.h"
#include "opids.h"
class Aggregator;
class RowRenderer;

class BlobColumn : public Column {
public:
    class Constant;
    class Reference;
    template <class T>
    class Callback;

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

template <class T>
class BlobColumn::Callback : public BlobColumn {
public:
    struct File;
    Callback(const std::string &name, const std::string &description,
             const ColumnOffsets &offsets,
             std::function<std::vector<char>(const T &)> f)
        : BlobColumn{name, description, offsets}, get_value_{std::move(f)} {}
    ~Callback() override = default;
    [[nodiscard]] std::unique_ptr<std::vector<char>> getValue(
        Row row) const override {
        const T *data = columnData<T>(row);
        return std::make_unique<std::vector<char>>(
            data == nullptr ? std::vector<char>{} : get_value_(*data));
    }

private:
    const std::function<std::vector<char>(const T &)> get_value_;
};

class BlobColumn::Constant : public BlobColumn {
public:
    Constant(std::string name, std::string description, std::vector<char> v)
        : BlobColumn(std::move(name), std::move(description), {})
        , v{std::move(v)} {};
    ~Constant() override = default;
    [[nodiscard]] std::unique_ptr<std::vector<char>> getValue(
        Row /*row*/) const override {
        return std::make_unique<std::vector<char>>(v);
    }

private:
    const std::vector<char> v;
};

class BlobColumn::Reference : public BlobColumn {
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
struct BlobColumn::Callback<T>::File : BlobColumn::Callback<T> {
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
        , _logger{
              Logger::getLogger("cmk.livestatus"),
              // Logger-lambda from Column::Column.
              [](std::ostream &os) { os << "[" << getThreadName() << "] "; }} {}
    std::vector<char> operator()(const T & /*data*/) const;
    Logger *logger() const { return &_logger; }

private:
    const std::function<std::filesystem::path()> _basepath;
    const std::function<std::filesystem::path(const T &)> _filepath;
    mutable ContextLogger _logger;
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
BlobColumn::Callback<T>::File::File(
    const std::string &name, const std::string &description,
    const ColumnOffsets &offsets,
    const std::function<std::filesystem::path()> &basepath,
    std::function<std::filesystem::path(const T &)> filepath)
    : BlobColumn::Callback<T>{name, description, offsets,
                              detail::FileImpl{basepath, std::move(filepath)}} {
}

#endif  // BlobColumn_h
