// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef RegExp_h
#define RegExp_h

#include <memory>
#include <string>

class RegExp {
public:
    enum class Case { ignore, respect };
    enum class Syntax { pattern, literal };

    // Standard pimpl boileplate code, see Scott Meyer's "Effective Modern C++",
    // item 22: "When using the Pimpl Idiom, define special member functions in
    // the implementation file."
    RegExp(const std::string &str, Case c, Syntax s);
    ~RegExp();
    RegExp(const RegExp &rhs) = delete;
    RegExp &operator=(const RegExp &rhs) = delete;
    RegExp(RegExp &&rhs) noexcept;
    RegExp &operator=(RegExp &&rhs) noexcept;

    [[nodiscard]] std::string replace(const std::string &str,
                                      const std::string &replacement) const;
    [[nodiscard]] bool match(const std::string &str) const;
    [[nodiscard]] bool search(const std::string &str) const;

    static std::string engine();

private:
    class Impl;
    std::unique_ptr<Impl> _impl;
};

#endif  // RegExp_h
