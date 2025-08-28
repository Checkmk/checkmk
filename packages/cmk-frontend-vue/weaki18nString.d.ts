/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * We strongly type translated strings to avoid accidental usage of non-translated
 * strings in places where translated strings are expected.
 *
 * This file exists to overwrite that strong type in the tests and demo. This saves us
 * from having to cast every single string in these environments.
 */
declare module '@/lib/i18nString' {
  export type TranslatedString = string
}
