// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef overload_h
#define overload_h

// A generic overload function, see e.g.
//    * http://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p0051r3.pdf
//    * https://www.bfilipek.com/2018/06/variant.html#overload
//    * https://arne-mertz.de/2018/05/overload-build-a-variant-visitor-on-the-fly/

namespace mk {

template <typename... Ts>
struct overload : Ts... {
    using Ts::operator()...;
};

template <typename... Ts>
overload(Ts...) -> overload<Ts...>;

}  // namespace mk

#endif  // overload_h
