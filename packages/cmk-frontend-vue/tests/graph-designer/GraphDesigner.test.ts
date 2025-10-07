/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { type GraphLines, type GraphOptions } from 'cmk-shared-typing/typescript/graph_designer'

import GraphDesignerApp from '@/graph-designer/GraphDesignerApp.vue'

async function fakeGraphRenderer(
  _graphId: string,
  _graphLines: GraphLines,
  _graphOptions: GraphOptions,
  _container: HTMLDivElement
) {
  return
}

test('Render GraphDesignerApp', () => {
  render(GraphDesignerApp, {
    props: {
      graph_id: 'graph id',
      graph_lines: [],
      graph_options: {
        unit: 'first_entry_with_unit',
        explicit_vertical_range: 'auto',
        omit_zero_metrics: true
      },
      metric_backend_available: false,
      graph_renderer: fakeGraphRenderer
    }
  })
})
