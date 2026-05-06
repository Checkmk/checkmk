/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { fireEvent, render, screen } from '@testing-library/vue'
import { type GraphLines } from 'cmk-shared-typing/typescript/graph_designer'
import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'

import GraphDesignerApp from '@/graph-designer/GraphDesignerApp.vue'
import { type AjaxGraph } from '@/graph-designer/private/graph.ts'

const server = setupServer(
  http.post('ajax_fetch_ajax_graph.py', () => {
    return HttpResponse.json({ result_code: 0, result: {} })
  })
)

beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }))
afterAll(() => server.close())

async function fakeGraphRenderer(_ajaxGraph: AjaxGraph, _container: HTMLDivElement) {
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
      create_services_available: false,
      graph_renderer: fakeGraphRenderer
    }
  })
})

describe('Constant graph line empty-value validation', () => {
  test('inline error does not appear before submit, even when value is cleared', async () => {
    const graphLines: GraphLines = [
      {
        id: 0,
        type: 'constant',
        color: '#ff0000',
        auto_title: 'Constant 100',
        custom_title: '',
        visible: true,
        line_type: 'line',
        mirrored: false,
        value: 100
      }
    ]

    render(GraphDesignerApp, {
      props: {
        graph_id: 'constant_inline_pre_submit',
        graph_lines: graphLines,
        graph_options: {
          unit: 'first_entry_with_unit',
          explicit_vertical_range: 'auto',
          omit_zero_metrics: true
        },
        metric_backend_available: false,
        create_services_available: false,
        graph_renderer: fakeGraphRenderer
      }
    })

    const constantInput = screen.getByDisplayValue('100')
    await userEvent.clear(constantInput)

    expect(screen.queryByText('Constant value must be a valid number')).not.toBeInTheDocument()
  })

  test('inline error appears after submit when value is cleared', async () => {
    const graphLines: GraphLines = [
      {
        id: 0,
        type: 'constant',
        color: '#ff0000',
        auto_title: 'Constant 100',
        custom_title: '',
        visible: true,
        line_type: 'line',
        mirrored: false,
        value: 100
      }
    ]

    render(GraphDesignerApp, {
      props: {
        graph_id: 'constant_inline_post_submit',
        graph_lines: graphLines,
        graph_options: {
          unit: 'first_entry_with_unit',
          explicit_vertical_range: 'auto',
          omit_zero_metrics: true
        },
        metric_backend_available: false,
        create_services_available: false,
        graph_renderer: fakeGraphRenderer
      }
    })

    const constantInput = screen.getByDisplayValue('100')
    await userEvent.clear(constantInput)

    const form = document.createElement('form')
    document.body.appendChild(form)
    void fireEvent.submit(form)

    await screen.findByText('Constant value must be a valid number')
  })
})
