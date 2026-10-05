/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

/** How long until the dialog reappears, as the screens name it: "48 hours", "7 days". */
export function formatRepromptInterval(hours: number): TranslatedString {
  const { _tn } = usei18n()
  // "48 hours" reads better than "2 days", and 100 hours make no whole number of days.
  if (hours < 72 || hours % 24 !== 0) {
    return _tn('%{n} hour', '%{n} hours', hours, { n: hours })
  }
  const days = hours / 24
  return _tn('%{n} day', '%{n} days', days, { n: days })
}
