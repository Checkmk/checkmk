// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#pragma once
#if !defined(___RAII_H)
#define ___RAII_H
// **********************************************************
// ON_OUT_OF_SCOPE: Usage example
// NOTE 1: This is a SUPPLEMENT for full-featured RAAI.
// NOTE 2: Do not overuse
// 1.
// FILE * fp = fopen("tmp.txt", "w");
// ON_OUT_OF_SCOPE( { puts("close file now"); if (fp) fclose(fp); } );
// 2.
// auto tmp_data  = new char[10000];
// ON_OUT_OF_SCOPE( delete tmp_data; );
// **********************************************************
namespace {
template <typename T>
struct InternalScopeGuard {
    T deleter_;
    InternalScopeGuard(T deleter) : deleter_(deleter) {}
    ~InternalScopeGuard() { deleter_(); }
};
}  // namespace
#define UNI_NAME(name, line) name##line

#define ON_OUT_OF_SCOPE_2(lambda_body, line)                                \
    auto UNI_NAME(deleter_lambda_, line) = [&]() { lambda_body; };          \
    InternalScopeGuard<decltype(UNI_NAME(deleter_lambda_, line))> UNI_NAME( \
        scope_guard_, line)(UNI_NAME(deleter_lambda_, line))

#define ON_OUT_OF_SCOPE(lambda_body) ON_OUT_OF_SCOPE_2(lambda_body, __LINE__)

#endif  // ___RAAI_H
