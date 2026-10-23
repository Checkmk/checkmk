/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Suggestions } from 'cmk-ui-library/components/CmkSuggestions'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import { type ItemType, LINE_TYPES, type LineType } from '../types'

export interface RowLabels {
  sourceTypeLabel: (type: ItemType) => TranslatedString
  lineStyleSuggestions: Suggestions
  lineStyleLabel: TranslatedString
}

export function useRowLabels(): RowLabels {
  const { _t } = usei18n()

  const sourceTypeLabels: Record<ItemType, TranslatedString> = {
    rrd_metric: _t('Checkmk RRD'),
    rrd_query: _t('Checkmk RRD'),
    telemetry_metrics: _t('Metrics backend'),
    constant: _t('Constant line'),
    scalar: _t('Service reference line'),
    rrd_formula: _t('Calculated metric')
  }

  const lineStyleTitles: Record<LineType, TranslatedString> = {
    line: _t('Line'),
    area: _t('Area'),
    stack: _t('Stack')
  }

  return {
    sourceTypeLabel: (type: ItemType) => sourceTypeLabels[type],
    lineStyleSuggestions: {
      type: 'fixed',
      suggestions: LINE_TYPES.map((lineType) => ({
        name: lineType,
        title: lineStyleTitles[lineType]
      }))
    },
    lineStyleLabel: _t('Line style')
  }
}
