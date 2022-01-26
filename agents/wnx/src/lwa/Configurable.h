// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef Configurable_h
#define Configurable_h

#include <sstream>
#include <string>

#include "Configuration.h"
#include "SettingsCollector.h"
#include "stringutil.h"
#include "types.h"

class ConfigurableBase {
public:
    explicit ConfigurableBase() : changed_(false) {}
    virtual ~ConfigurableBase() = default;
    ConfigurableBase(const ConfigurableBase &) = delete;
    ConfigurableBase &operator=(const ConfigurableBase &) = delete;

    void changed() { changed_ = true; }
    auto isChanged() const { return changed_; }
    std::string iniString() const { return string_value_; }

    virtual void feed(const std::string &key, const std::string &value) = 0;
    virtual void output(const std::string &key, std::ostream &out) const = 0;
    virtual std::string outputForYaml() { return string_value_; }
    virtual std::string outputAsInternalArray() { return ""; }
    virtual void startFile() = 0;
    virtual void startBlock() = 0;
    virtual bool isKeyed() const { return false; }
    virtual bool isListed() const { return false; }
    virtual std::vector<std::pair<std::string, std::string>> generateKeys() {
        return {};
    }

protected:
    std::string string_value_;
    bool changed_;
};

template <typename ValueT>
class Configurable : public ConfigurableBase {
public:
    Configurable(Configuration &config, const char *section, const char *key,
                 const ValueT &def)
        : _value(def) {
        config.reg(section, key, this);
    }

    virtual ~Configurable() = default;

    ValueT *operator->() { return &_value; }

    const ValueT *operator->() const { return &_value; }

    ValueT &operator*() { return _value; }

    const ValueT &operator*() const { return _value; }

    virtual void startFile() override {}
    virtual void startBlock() override {}

    virtual void feed(const std::string &, const std::string &value) override {
        startBlock();
        string_value_ = value;
        _value = from_string<ValueT>(value);
    }

    virtual void output(const std::string &key,
                        std::ostream &out) const override {
        out << key << " = " << _value << "\n";
    }

    virtual std::string outputForYaml() {
        std::stringstream ss;
        ss << _value;
        return ss.str();
    }

private:
    ValueT _value;
};

// This is a TMP, we want to convert filesystem path to std::string, but leave
// all other types as is to prevent quotation!
template <typename T, typename T2 = T>
T2 RemoveFilesystemPath(const T &val) {
    return val;
}

std::string RemoveFilesystemPath(const std::filesystem::path &val) {
    return val.string<char, std::char_traits<char>>();
}

/**
 * regular list collector which allows multiple assignments to the same
 * variable. The addmode and block mode decide how these multiple assignments
 * are combined
 **/
template <typename ContainerT, typename BlockModeT = BlockMode::Nop<ContainerT>,
          typename AddModeT = AddMode::Append<ContainerT>>
class ListConfigurable : public ConfigurableBase {
    using DataT = typename ContainerT::value_type;

public:
    ListConfigurable(Configuration &config, const char *section,
                     const char *key) {
        config.reg(section, key, this);
    }

    virtual ~ListConfigurable() = default;

    ContainerT *operator->() { return &_values; }

    const ContainerT *operator->() const { return &_values; }

    ContainerT &operator*() { return _values; }

    const ContainerT &operator*() const { return _values; }
    virtual bool isListed() const { return true; }

    virtual void startFile() {
        _add_mode.startFile(_values);
        _block_mode.startFile(_values);
    }

    virtual void startBlock() { _block_mode.startBlock(_values); }

    virtual void feed(const std::string &, const std::string &value) override {
        try {
            this->add(from_string<DataT>(value));
        } catch (const StringConversionError &e) {
            std::cerr << e.what() << std::endl;
        }
    }

    virtual void output(const std::string &key,
                        std::ostream &out) const override {
        for (const DataT &data : _values) {
            auto v = RemoveFilesystemPath(data);
            out << key << " = " << v << "\n";
        }
    }

    /**
     * returns whether there ever was an assignment to this configurable
     **/
    bool wasAssigned() const { return _was_assigned; }

    virtual void clear() { _values.clear(); }

    // only valid with a grouping adder. it's important to understand that
    // due to how templates in C++ work, these functions are not compiled
    // for template-instantiations where they aren't used so even though
    // they wouldn't compile with non-grouping adders, this is not a
    // problem. (google SFINAE)
    void setGroupFunction(
        typename AddMode::PriorityAppendGrouped<ContainerT>::GroupFunction
            function) {
        _add_mode.setGroupFunction(function);
    }

    bool feedInner(const std::string &key, const std::string &value) {
        return _add_mode.addGroup(_values, key.c_str(), value.c_str());
    }

    void add(const DataT &data) {
        _add_mode.add(_values, data);
        _was_assigned = true;
    }

    virtual std::string outputForYaml() {
        std::stringstream ss;
        if (_values.size() == 0) return "~";
        for (auto &c : _values) {
            ss << ToYamlString(c, true) << "\n";
            // ss << ",";
        }

        return ss.str();
    }

    // "check_mk mem df"
    std::string outputAsInternalArray() override {
        std::stringstream ss;
        if (_values.size() == 0) return "~";

        for (auto &c : _values) {
            ss << c << " ";
        }
        auto str = ss.str();

        if (!str.empty() && str.back() == ' ') str.pop_back();
        return str;
    }

protected:
    ContainerT &values() { return _values; }

    const ContainerT &values() const { return _values; }

private:
    ContainerT _values;
    BlockModeT _block_mode;
    AddModeT _add_mode;

    bool _was_assigned{false};
};

template <typename DataT>
class KeyedListConfigurable : public ConfigurableBase {
    using ContainerT = std::vector<std::pair<std::string, DataT>>;

public:
    KeyedListConfigurable(Configuration &config, const char *section,
                          const char *key) {
        config.reg(section, key, this);
    }

    virtual ~KeyedListConfigurable() = default;

    virtual bool isKeyed() const { return true; }
    virtual std::vector<std::pair<std::string, std::string>> generateKeys() {
        std::vector<std::pair<std::string, std::string>> out;
        for (auto &v : _values)
            out.push_back({v.first, std::to_string(v.second)});
        return out;
    }

    virtual void feed(const std::string &var,
                      const std::string &value) override {
        size_t pos = var.find_first_of(" ");
        std::string key;
        if (pos != std::string::npos) {
            key = std::string(var.begin() + pos + 1, var.end());
        }
        startBlock();
        try {
            _add_mode.add(_values,
                          std::make_pair(key, from_string<DataT>(value)));
        } catch (const StringConversionError &e) {
            std::cerr << e.what() << std::endl;
        }
    }

    // in this fantastic file you found piece of sh$t code
    // which breaks clang-format
    // clang-format is our friend
#include "ConfigurableTrash.h"

    ContainerT *operator->() { return &_values; }

    const ContainerT *operator->() const { return &_values; }

    ContainerT &operator*() { return _values; }

    const ContainerT &operator*() const { return _values; }

    virtual void startFile() override { _add_mode.startFile(_values); }
    virtual void startBlock() override {}

    void clear() { _values.clear(); }

    void add(const DataT &data) { _add_mode.add(_values, data); }

protected:
    ContainerT &values() { return _values; }

    const ContainerT &values() const { return _values; }

private:
    ContainerT _values;
    AddMode::PriorityAppend<ContainerT> _add_mode;
};

/**
 * Splitting list configurable produces a list of items but expects all
 * elements in a single assignment, separated by a separator
 **/
template <typename ContainerT, typename BlockModeT = BlockMode::Nop<ContainerT>,
          typename AddModeT = AddMode::Append<ContainerT>>
class SplittingListConfigurable
    : public ListConfigurable<ContainerT, BlockModeT, AddModeT> {
    using SuperT = ListConfigurable<ContainerT, BlockModeT, AddModeT>;
    using DataT = typename ContainerT::value_type;
    using MapFunction = std::function<std::string(const std::string &)>;

public:
    SplittingListConfigurable(
        Configuration &config, const char *section, const char *key,
        const MapFunction &mapFunction = [](const std::string &s) { return s; },
        char split_char = ' ')
        : SuperT(config, section, key)
        , _mapFunction(mapFunction)
        , _split_char(split_char) {}

    virtual ~SplittingListConfigurable() = default;

    virtual void feed(const std::string &key,
                      const std::string &value) override {
        SuperT::clear();
        std::stringstream str(value);
        std::string item;
        while (getline(str, item, _split_char)) {
            SuperT::feed(key, _mapFunction(item));
        }
    }

    virtual void output(const std::string &key,
                        std::ostream &out) const override {
        out << key << " =";
        for (const DataT &data : this->values()) {
            out << " " << data;
        }
        out << "\n";
    }

private:
    const MapFunction _mapFunction;
    char _split_char;
};

#endif  // Configurable_h
