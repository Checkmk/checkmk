// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

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
}  // namespace BlockMode

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
 * that within a configuration file, entries are appended but the entries of
 * later files are put before those of earlier files
 */
template <typename ContainerT>
class PriorityAppend {
public:
    void startFile(ContainerT &list) { _insert_pos = list.begin(); }
    void add(ContainerT &list, const typename ContainerT::value_type &value) {
        // this inserts the value before the iterator which is at the beginning
        // of the previous file-block (see startFile). If this is the first
        // file,
        // this is the end of the list.
        _insert_pos = list.insert(_insert_pos, value) + 1;
    }

private:
    typename ContainerT::iterator _insert_pos;
};

/**
 * Adder that works with unsorted containers
 */
template <typename ContainerT>
class SetInserter {
public:
    void startFile(ContainerT &) {}
    void add(ContainerT &set,
             const typename ContainerT::value_type &value) const {
        set.insert(value);
    }
};

/**
 * appender that can deal with multiline configurations
 * the top-most line of each group is added using the regular "add" function,
 * the rest using addGroup. The functor needs to handle the key-value pair and
 * insert it to the object directly.
 */
template <typename ContainerT>
class PriorityAppendGrouped {
public:
    using GroupFunction = void (*)(typename ContainerT::value_type &,
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
}  // namespace AddMode

#endif  // SETTINGS_COLLECTOR_H
