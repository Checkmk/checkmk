/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

/**
 * We strongly type translated strings to avoid accidental usage of non-translated
 * strings in places where translated strings are expected.
 *
 * This file exists by itself to allow it to be overwritten in the case of the tests
 * and demo. In these cases, casting is not necessary.
 */
export type TranslatedString = string & { readonly __translated__: unique symbol }
