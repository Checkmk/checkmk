/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

export interface TimeRangePresetItem {
  /** Unique within a row; also the option name inside the overflow dropdown. */
  name: string
  title: TranslatedString
}
