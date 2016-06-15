// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2015             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#ifndef SETTINGS_COLLECTOR_H
#define SETTINGS_COLLECTOR_H

#include <algorithm>
#include <set>
#include <vector>

namespace BlockMode {
// keep everything
template <typename ContainerT>
class Nop {
public:
    void startFile(ContainerT &) {}
    void startBlock(ContainerT &) {}
};

// only the last block of this setting has an effect
template <typename ContainerT>
class BlockExclusive {
public:
    void startFile(ContainerT &) {}
    void startBlock(ContainerT &data) { data.clear(); }
};

// only the last file with this setting has an effect
template <typename ContainerT>
class FileExclusive {
public:
    void startFile(ContainerT &) { m_ClearPending = true; }
    void startBlock(ContainerT &data) {
        if (m_ClearPending) {
            data.clear();
            m_ClearPending = false;
        }
    }

private:
    bool m_ClearPending;
};
}

namespace AddMode {
/**
 * regular appender. Always adds elements to the end of the list
 */
template <typename ContainerT>
class Append {
public:
    void startFile(ContainerT &) {}
    void add(ContainerT &list,
             const typename ContainerT::value_type &value) const {
        list.push_back(value);
    }
};

/**
 * appender that gives priority to files in the order they appear. This means
 * that
 * within a configuration file, entries are appended but the entries of later
 * files
 * are put before those of earlier files
 */
template <typename ContainerT>
class PriorityAppend {
public:
    void startFile(ContainerT &list) { _insert_pos = list.begin(); }
    void add(ContainerT &list, const typename ContainerT::value_type &value) {
        // this inserts the value before the iterator which is at the beginning
        // of
        // the previous file-block (see startFile). If this is the first file,
        // this is
        // the end of the list.
        _insert_pos = list.insert(_insert_pos, value) + 1;
    }

private:
    typename ContainerT::iterator _insert_pos;
};

/**
 * appender that can deal with multiline configurations
 * the top-most line of each group is added using the regular "add" function,
 * the rest
 * using addGroup. The functor needs to handle the key-value pair and insert it
 * to the object
 * directly.
 */
template <typename ContainerT>
class PriorityAppendGrouped {
public:
    typedef void (*GroupFunction)(typename ContainerT::value_type &,
                                  const char *key, const char *value);

    void startFile(ContainerT &list) { _insert_pos = list.begin(); }
    void add(ContainerT &list, const typename ContainerT::value_type &value) {
        _insert_pos = list.insert(_insert_pos, value) + 1;
    }
    void setGroupFunction(GroupFunction function) { _function = function; }
    bool addGroup(ContainerT &list, const char *key, const char *value) {
        if (list.empty()) {
            return false;
        } else {
            _function(*(_insert_pos - 1), key, value);
            return true;
        }
    }

private:
    GroupFunction _function;
    typename ContainerT::iterator _insert_pos;
};
}

class Collector {
public:
    Collector();
    virtual ~Collector();

    virtual void startFile() = 0;
    virtual void startBlock() = 0;
    virtual void clear() = 0;
};

template <typename ContainerT, typename BlockModeT = BlockMode::Nop<ContainerT>,
          typename AddModeT = AddMode::Append<ContainerT> >
class ListCollector : public Collector {
    typedef typename ContainerT::value_type DataT;

public:
    virtual void startFile() {
        _add_mode.startFile(_values);
        _block_mode.startFile(_values);
    }

    virtual void startBlock() { _block_mode.startBlock(_values); }

    void add(const DataT &value) { _add_mode.add(_values, value); }

    virtual void clear() { _values.clear(); }

    ContainerT *operator->() { return &_values; }

    const ContainerT *operator->() const { return &_values; }

    ContainerT &operator*() { return _values; }

    const ContainerT &operator*() const { return _values; }

public:  // only valid with a grouping adder. it's important to understand that
         // due to how templates in C++ work, these functions are not compiled
         // for template-instantiations where they aren't used so even though
         // they wouldn't comple with non-grouping adders, this is not a
         // problem.
    void setGroupFunction(typename AddMode::PriorityAppendGrouped<
                          ContainerT>::GroupFunction function) {
        _add_mode.setGroupFunction(function);
    }

    bool addGroup(const char *key, const char *value) {
        return _add_mode.addGroup(_values, key, value);
    }

private:
    ContainerT _values;
    BlockModeT _block_mode;
    AddModeT _add_mode;
};

class CollectorRegistry {
public:
    static CollectorRegistry &instance();

    void startFile();

    // register a collector (sorry for the abbreviation but "register" is a
    // reserved keyword in
    // C++")
    void reg(Collector *collector) { _collectors.insert(collector); }

    void unreg(Collector *collector) { _collectors.erase(collector); }

private:
    std::set<Collector *> _collectors;
};

#endif  // SETTINGS_COLLECTOR_H
