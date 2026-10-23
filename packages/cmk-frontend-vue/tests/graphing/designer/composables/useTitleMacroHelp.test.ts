/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import type { TitleMacroGroup } from 'cmk-shared-typing/typescript/custom_graph_designer'
import { defineComponent } from 'vue'

import { useTitleMacroHelp } from '@/graphing/designer/composables/useTitleMacroHelp'

function mountHelp(): ReturnType<typeof useTitleMacroHelp> {
  let api!: ReturnType<typeof useTitleMacroHelp>
  render(
    defineComponent({
      setup() {
        api = useTitleMacroHelp()
        return () => null
      }
    })
  )
  return api
}

test('labels each source group and wraps its macros', () => {
  const { renderTitleMacroHelp } = mountHelp()
  const help = renderTitleMacroHelp([
    { source_type: 'rrd_metric', macros: ['$DEFAULT_TITLE$', '$METRIC_NAME$'] },
    { source_type: 'telemetry_metrics', macros: ['$SERIES_ID$'] }
  ])
  expect(help).toContain('Available title macros:')
  expect(help).toContain(
    '<b>Checkmk RRD (single)</b>: <tt>$DEFAULT_TITLE$</tt>, <tt>$METRIC_NAME$</tt>'
  )
  // Source types without a help-specific label fall back to the row label.
  expect(help).toContain('<b>Metrics backend</b>: <tt>$SERIES_ID$</tt>')
})

test('distinguishes the single metric from the dynamic query', () => {
  const { renderTitleMacroHelp } = mountHelp()
  const help = renderTitleMacroHelp([
    { source_type: 'rrd_metric', macros: ['$DEFAULT_TITLE$'] },
    { source_type: 'rrd_query', macros: ['$DEFAULT_TITLE$', '$SERIES_ID$'] }
  ])
  expect(help).toContain('<b>Checkmk RRD (single)</b>')
  expect(help).toContain('<b>Checkmk RRD (query)</b>')
})

test('renders in the frontend order, not the order the backend supplied', () => {
  const { renderTitleMacroHelp } = mountHelp()
  const scrambled: TitleMacroGroup[] = [
    { source_type: 'telemetry_metrics', macros: ['$SERIES_ID$'] },
    { source_type: 'rrd_query', macros: ['$SERIES_ID$'] },
    { source_type: 'rrd_metric', macros: ['$DEFAULT_TITLE$'] }
  ]
  const help = renderTitleMacroHelp(scrambled)
  expect(help.indexOf('Checkmk RRD (single)')).toBeLessThan(help.indexOf('Checkmk RRD (query)'))
  expect(help.indexOf('Checkmk RRD (query)')).toBeLessThan(help.indexOf('Metrics backend'))
})

test('skips source types absent from the given macros', () => {
  const { renderTitleMacroHelp } = mountHelp()
  const help = renderTitleMacroHelp([{ source_type: 'constant', macros: ['$DEFAULT_TITLE$'] }])
  expect(help).toContain('<b>Constant line</b>: <tt>$DEFAULT_TITLE$</tt>')
  expect(help).not.toContain('Checkmk RRD')
  expect(help).not.toContain('Metrics backend')
})
