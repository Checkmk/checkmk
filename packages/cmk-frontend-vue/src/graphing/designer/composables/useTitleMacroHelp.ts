/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type {
  TitleMacroGroup,
  TitleMacroSourceType
} from 'cmk-shared-typing/typescript/custom_graph_designer'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import { useRowLabels } from './useRowLabels'

// A source type absent from the order is silently dropped from the help, so require the tuple
// to cover every TitleMacroSourceType: an incomplete list makes the argument type `never`.
function everySourceType<const T extends readonly TitleMacroSourceType[]>(
  order: [TitleMacroSourceType] extends [T[number]] ? T : never
): T {
  return order
}

const HELP_SOURCE_ORDER = everySourceType([
  'rrd_metric',
  'rrd_query',
  'constant',
  'scalar',
  'rrd_formula',
  'telemetry_metrics'
])

export interface TitleMacroHelp {
  renderTitleMacroHelp: (titleMacros: TitleMacroGroup[]) => TranslatedString
}

/** Renders the Title-column help: the macros each source resolves, ordered and labelled here. */
export function useTitleMacroHelp(): TitleMacroHelp {
  const { _t } = usei18n()
  const { sourceTypeLabel } = useRowLabels()

  const helpLabels: Partial<Record<TitleMacroSourceType, TranslatedString>> = {
    rrd_metric: _t('Checkmk RRD (single)'),
    rrd_query: _t('Checkmk RRD (query)')
  }

  function renderTitleMacroHelp(titleMacros: TitleMacroGroup[]): TranslatedString {
    const macrosBySource = new Map(titleMacros.map((group) => [group.source_type, group.macros]))
    return untranslated(
      [
        _t('Available title macros:'),
        ...HELP_SOURCE_ORDER.flatMap((sourceType) => {
          const macros = macrosBySource.get(sourceType)
          if (macros === undefined) {
            return []
          }
          const label = helpLabels[sourceType] ?? sourceTypeLabel(sourceType)
          return [`<b>${label}</b>: ${macros.map((macro) => `<tt>${macro}</tt>`).join(', ')}`]
        })
      ].join('<br>')
    )
  }

  return { renderTitleMacroHelp }
}
