/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

export default function usei18n(_keyPrefix: string) {
  function t(_translationKey: string, defaultString: string): string {
    // This is a placeholder function for translation to allow developing with
    // frontend i18n in mind for 2.5.0 features so they don't need touching in
    // the backend.
    return defaultString
  }

  return { t }
}
