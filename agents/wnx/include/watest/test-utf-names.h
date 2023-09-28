// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.


// unicode strings difficult for git
// This is UTF-8 files, but may be changed to the UTF-16

#ifndef test_utf_names_h__
#define test_utf_names_h__
const auto test_u8_name = u8"愛.txt";
const auto test_russian_file = L"файл.тест";
auto const test_cyrillic = L"zZaВва";
auto const test_cyrillic_upper = L"ZZAВВА";
auto const test_cyrillic_lower = L"zzaвва";

#endif  // test_utf_names_h__
