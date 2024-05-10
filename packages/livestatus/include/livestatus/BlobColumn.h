// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef BlobColumn_h
#define BlobColumn_h

#include <chrono>
#include <filesystem>
#include <functional>
#include <iterator>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "livestatus/Column.h"
#include "livestatus/FileSystemHelper.h"
#include "livestatus/Filter.h"
#include "livestatus/Logger.h"
#include "livestatus/Renderer.h"
#include "livestatus/Row.h"
#include "livestatus/opids.h"
class Aggregator;
class RowRenderer;
class User;

template <typename T>
class BlobColumn : public Column {
public:
    BlobColumn(const std::string &name, const std::string &description,
               const ColumnOffsets &offsets,
               std::function<std::vector<char>(const T &)> f)
        : Column{name, description, offsets}, f_{std::move(f)} {}

    [[nodiscard]] ColumnType type() const override { return ColumnType::blob; }

    void output(Row row, RowRenderer &r, const User & /*user*/,
                std::chrono::seconds /*timezone_offset*/) const override {
        if (std::unique_ptr<std::vector<char>> blob = getValue(row)) {
            r.output(*blob);
        } else {
            r.output(Null());
        }
    }

    [[nodiscard]] std::unique_ptr<Filter> createFilter(
        Filter::Kind /*kind*/, RelationalOperator /*relOp*/,
        const std::string & /*value*/) const override {
        throw std::runtime_error("filtering on blob column '" + name() +
                                 "' not supported");
    }

    [[nodiscard]] std::unique_ptr<Sorter> createSorter() const override {
        throw std::runtime_error("sorting on blob column '" + name() +
                                 "' not supported");
    }

    [[nodiscard]] std::unique_ptr<Aggregator> createAggregator(
        AggregationFactory /*factory*/) const override {
        throw std::runtime_error("aggregating on blob column '" + name() +
                                 "' not supported");
    }

    [[nodiscard]] std::unique_ptr<std::vector<char>> getValue(Row row) const {
        const T *data = columnData<T>(row);
        return std::make_unique<std::vector<char>>(
            data == nullptr ? std::vector<char>{} : f_(*data));
    }

private:
    const std::function<std::vector<char>(const T &)> f_;
};

template <typename T>
class BlobFileReader {
public:
    explicit BlobFileReader(
        std::function<std::filesystem::path(const T &)> path)
        : _path{std::move(path)}, _logger{"cmk.livestatus"} {}

    std::vector<char> operator()(const T &data) const {
        const auto path = _path(data);
        if (!std::filesystem::exists(path)) {
            // The path is not configured.
            return {};
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

    Logger *logger() const { return &_logger; }

private:
    const std::function<std::filesystem::path(const T &)> _path;
    mutable ThreadNameLogger _logger;
};

#endif  // BlobColumn_h
