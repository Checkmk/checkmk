/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { type GraphLines } from 'cmk-shared-typing/typescript/graph_designer'
import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'

import { initializeComponentRegistry } from '@/form/private/FormEditDispatcher/dispatch'

import GraphDesignerApp from '@/graph-designer/GraphDesignerApp.vue'
import { type AjaxGraph } from '@/graph-designer/private/graph.ts'

initializeComponentRegistry()

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

async function selectDropdownOption(dropdownLabel: string, optionName: string) {
  const dropdown = await screen.findByRole('combobox', { name: dropdownLabel })
  await waitFor(() => expect(dropdown).toBeEnabled(), { timeout: 10000 })
  void userEvent.click(dropdown)
  const option = await screen.findByRole('option', { name: optionName }, { timeout: 10000 })
  await userEvent.click(option)
}

const graphLineTypesExceptQuery = [
  'sum',
  'product',
  'difference',
  'fraction',
  'average',
  'minimum',
  'maximum'
] as const

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

test('Graph lines table is empty when no graph lines are provided', () => {
  render(GraphDesignerApp, {
    props: {
      graph_id: 'empty_graph',
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

  const table = screen.getByRole('table', { name: 'Graph lines' })
  expect(table).toBeInTheDocument()

  const graphLineRows = screen.queryAllByRole('row', { name: /^Graph line / })
  expect(graphLineRows.length).toBe(0)
})

test('Graph lines table is not empty when graph lines are provided', () => {
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
      graph_id: 'non_empty_graph',
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

  const table = screen.getByRole('table', { name: 'Graph lines' })
  expect(table).toBeInTheDocument()

  const expectedGraphLine = screen.getByRole('row', { name: 'Graph line Constant 100' })
  expect(expectedGraphLine).toBeInTheDocument()
})

test.each(graphLineTypesExceptQuery)('Graph line of type %s can be edited', (lineType) => {
  const graphLines: GraphLines = [
    {
      id: 0,
      type: 'query',
      color: '#ff0000',
      auto_title: 'Constant 100',
      custom_title: '',
      visible: true,
      line_type: 'line',
      mirrored: false,
      metric_name: 'test_metric',
      resource_attributes: [],
      scope_attributes: [],
      data_point_attributes: [],
      aggregation_lookback: 60,
      aggregation_histogram_percentile: 95
    }
  ]

  render(GraphDesignerApp, {
    props: {
      graph_id: 'editable_graph_line',
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

  // Make sure there is no such checkbox for query graph line
  const selectionCheckbox = screen.queryByLabelText('Select graph line to edit')
  expect(selectionCheckbox).not.toBeInTheDocument()

  graphLines[0]!.type = lineType

  render(GraphDesignerApp, {
    props: {
      graph_id: 'editable_graph_line',
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

  const updatedSelectionCheckbox = screen.getByLabelText('Select graph line to edit')
  expect(updatedSelectionCheckbox).toBeInTheDocument()
})

test.each(graphLineTypesExceptQuery)('Graph line of type %s has dissolve button', (lineType) => {
  const graphLines: GraphLines = [
    {
      id: 0,
      type: lineType,
      color: '#ff0000',
      auto_title: `Operation of type ${lineType}`,
      custom_title: '',
      visible: true,
      line_type: 'line',
      mirrored: false,
      operands: []
    }
  ]

  render(GraphDesignerApp, {
    props: {
      graph_id: 'dissolvable_graph_line',
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

  const graphLineRow = screen.getByRole('row', {
    name: `Graph line Operation of type ${lineType}`
  })
  expect(graphLineRow).toBeInTheDocument()

  const dissolveButton = screen.getByRole('button', { name: 'Dissolve operation' })
  expect(dissolveButton).toBeInTheDocument()
})

test("Graph line of type 'query' has 'Add rule: Metric backend (Custom query)' button", () => {
  const graphLines: GraphLines = [
    {
      id: 0,
      type: 'query',
      color: '#ff0000',
      auto_title: 'Query line',
      custom_title: '',
      visible: true,
      line_type: 'line',
      mirrored: false,
      metric_name: 'test_metric',
      resource_attributes: [],
      scope_attributes: [],
      data_point_attributes: [],
      aggregation_lookback: 60,
      aggregation_histogram_percentile: 95
    }
  ]

  render(GraphDesignerApp, {
    props: {
      graph_id: 'query_graph_line',
      graph_lines: graphLines,
      graph_options: {
        unit: 'first_entry_with_unit',
        explicit_vertical_range: 'auto',
        omit_zero_metrics: true
      },
      metric_backend_available: false,
      create_services_available: true,
      graph_renderer: fakeGraphRenderer
    }
  })

  const addRuleButton = screen.getByRole('button', {
    name: 'Add rule: Metric backend (Custom query)'
  })
  expect(addRuleButton).toBeInTheDocument()
})

test.each(graphLineTypesExceptQuery)(
  "Graph line of type %s has 'Add rule: Metric backend (Custom query)' button",
  (lineType) => {
    const graphLines: GraphLines = [
      {
        id: 0,
        type: lineType,
        color: '#ff0000',
        auto_title: `Operation of type ${lineType}`,
        custom_title: '',
        visible: true,
        line_type: 'line',
        mirrored: false,
        operands: []
      }
    ]

    render(GraphDesignerApp, {
      props: {
        graph_id: 'non_query_graph_line',
        graph_lines: graphLines,
        graph_options: {
          unit: 'first_entry_with_unit',
          explicit_vertical_range: 'auto',
          omit_zero_metrics: true
        },
        metric_backend_available: false,
        create_services_available: true,
        graph_renderer: fakeGraphRenderer
      }
    })

    const addRuleButton = screen.queryByRole('button', {
      name: 'Add rule: Metric backend (Custom query)'
    })
    expect(addRuleButton).not.toBeInTheDocument()
  }
)

test("Graph line of type 'query' does not have Color picker button", () => {
  const graphLines: GraphLines = [
    {
      id: 0,
      type: 'query',
      color: '#ff0000',
      auto_title: 'Query line',
      custom_title: '',
      visible: true,
      line_type: 'line',
      mirrored: false,
      metric_name: 'test_metric',
      resource_attributes: [],
      scope_attributes: [],
      data_point_attributes: [],
      aggregation_lookback: 60,
      aggregation_histogram_percentile: 95
    }
  ]

  render(GraphDesignerApp, {
    props: {
      graph_id: 'query_graph_line',
      graph_lines: graphLines,
      graph_options: {
        unit: 'first_entry_with_unit',
        explicit_vertical_range: 'auto',
        omit_zero_metrics: true
      },
      metric_backend_available: false,
      create_services_available: true,
      graph_renderer: fakeGraphRenderer
    }
  })

  const colorPickerButton = screen.queryByLabelText('Color picker')
  expect(colorPickerButton).not.toBeInTheDocument()
})

test.each(graphLineTypesExceptQuery)(
  'Graph line of type %s has Color picker button',
  (lineType) => {
    const graphLines: GraphLines = [
      {
        id: 0,
        type: lineType,
        color: '#ff0000',
        auto_title: `Operation of type ${lineType}`,
        custom_title: '',
        visible: true,
        line_type: 'line',
        mirrored: false,
        operands: []
      }
    ]

    render(GraphDesignerApp, {
      props: {
        graph_id: 'color_picker_graph_line',
        graph_lines: graphLines,
        graph_options: {
          unit: 'first_entry_with_unit',
          explicit_vertical_range: 'auto',
          omit_zero_metrics: true
        },
        metric_backend_available: false,
        create_services_available: true,
        graph_renderer: fakeGraphRenderer
      }
    })

    const colorPickerButton = screen.getByLabelText('Color picker')
    expect(colorPickerButton).toBeInTheDocument()
  }
)

test("Graph line of type 'query' has help text", () => {
  const graphLines: GraphLines = [
    {
      id: 0,
      type: 'query',
      color: '#ff0000',
      auto_title: 'Query line',
      custom_title: '',
      visible: true,
      line_type: 'line',
      mirrored: false,
      metric_name: 'test_metric',
      resource_attributes: [],
      scope_attributes: [],
      data_point_attributes: [],
      aggregation_lookback: 60,
      aggregation_histogram_percentile: 95
    }
  ]

  render(GraphDesignerApp, {
    props: {
      graph_id: 'query_graph_line',
      graph_lines: graphLines,
      graph_options: {
        unit: 'first_entry_with_unit',
        explicit_vertical_range: 'auto',
        omit_zero_metrics: true
      },
      metric_backend_available: false,
      create_services_available: true,
      graph_renderer: fakeGraphRenderer
    }
  })

  const helpTextElement = screen.getByLabelText('Help: Metric backend (Custom query)')
  expect(helpTextElement).toBeInTheDocument()
})

test.each(graphLineTypesExceptQuery)(
  'Graph line of type %s does not have help text',
  (lineType) => {
    const graphLines: GraphLines = [
      {
        id: 0,
        type: lineType,
        color: '#ff0000',
        auto_title: `Operation of type ${lineType}`,
        custom_title: '',
        visible: true,
        line_type: 'line',
        mirrored: false,
        operands: []
      }
    ]

    render(GraphDesignerApp, {
      props: {
        graph_id: 'non_query_graph_line',
        graph_lines: graphLines,
        graph_options: {
          unit: 'first_entry_with_unit',
          explicit_vertical_range: 'auto',
          omit_zero_metrics: true
        },
        metric_backend_available: false,
        create_services_available: true,
        graph_renderer: fakeGraphRenderer
      }
    })

    const helpTextElement = screen.queryByLabelText('Help: Metric backend (Custom query)')
    expect(helpTextElement).not.toBeInTheDocument()
  }
)

test("Graph line of type 'query' has inline help text", () => {
  const graphLines: GraphLines = [
    {
      id: 0,
      type: 'query',
      color: '#ff0000',
      auto_title: 'Query line',
      custom_title: '',
      visible: true,
      line_type: 'line',
      mirrored: false,
      metric_name: 'test_metric',
      resource_attributes: [],
      scope_attributes: [],
      data_point_attributes: [],
      aggregation_lookback: 60,
      aggregation_histogram_percentile: 95
    }
  ]

  render(GraphDesignerApp, {
    props: {
      graph_id: 'query_graph_line',
      graph_lines: graphLines,
      graph_options: {
        unit: 'first_entry_with_unit',
        explicit_vertical_range: 'auto',
        omit_zero_metrics: true
      },
      metric_backend_available: false,
      create_services_available: true,
      graph_renderer: fakeGraphRenderer
    }
  })

  const inlineHelpTextElement = screen.getByLabelText('Inline Help: Metric backend (Custom query)')
  expect(inlineHelpTextElement).toBeInTheDocument()
})

test.each(graphLineTypesExceptQuery)(
  'Graph line of type %s does not have inline help text',
  (lineType) => {
    const graphLines: GraphLines = [
      {
        id: 0,
        type: lineType,
        color: '#ff0000',
        auto_title: `Operation of type ${lineType}`,
        custom_title: '',
        visible: true,
        line_type: 'line',
        mirrored: false,
        operands: []
      }
    ]

    render(GraphDesignerApp, {
      props: {
        graph_id: 'non_query_graph_line',
        graph_lines: graphLines,
        graph_options: {
          unit: 'first_entry_with_unit',
          explicit_vertical_range: 'auto',
          omit_zero_metrics: true
        },
        metric_backend_available: false,
        create_services_available: true,
        graph_renderer: fakeGraphRenderer
      }
    })

    const inlineHelpTextElement = screen.queryByLabelText(
      'Inline Help: Metric backend (Custom query)'
    )
    expect(inlineHelpTextElement).not.toBeInTheDocument()
  }
)

// This is an integration test that covers the whole flow including the mocked
// autocompleter interaction, so we need to increase the default timeout for this test.
describe('Adding a Query graph line', { timeout: 20_000 }, () => {
  beforeAll(() => {
    type Id = string
    type Value = string
    const choicesByIdent: Record<string, Array<{ id: Id; value: Value }>> = {
      monitored_metrics_backend: [{ id: 'dummy_metric_name', value: 'Dummy Metric Name' }],
      monitored_resource_attributes_keys_backend: [
        { id: 'dummy_resource_attribute_key', value: 'Dummy Resource Attribute key' }
      ],
      monitored_resource_attributes_values_backend: [
        { id: 'dummy_resource_attribute_value', value: 'Dummy Resource Attribute value' }
      ],
      monitored_scope_attributes_keys_backend: [
        { id: 'dummy_scope_attribute_key', value: 'Dummy Scope Attribute key' }
      ],
      monitored_scope_attributes_values_backend: [
        { id: 'dummy_scope_attribute_value', value: 'Dummy Scope Attribute value' }
      ],
      monitored_data_point_attributes_keys_backend: [
        { id: 'dummy_data_point_attribute_key', value: 'Dummy Data Point Attribute key' }
      ],
      monitored_data_point_attributes_values_backend: [
        { id: 'dummy_data_point_attribute_value', value: 'Dummy Data Point Attribute value' }
      ]
    }

    function autocompleteInterceptor({
      params
    }: {
      params: Record<string, string | readonly string[] | undefined>
    }) {
      const ident = params['autocompleter'] as string
      return HttpResponse.json({
        choices: choicesByIdent[ident] || []
      })
    }

    server.use(
      http.post(
        `${location.protocol}//${location.host}/api/1.0/objects/autocomplete/:autocompleter`,
        autocompleteInterceptor
      )
    )
  })

  afterAll(() => {
    server.resetHandlers()
  })

  test.skip('works as expected', async () => {
    render(GraphDesignerApp, {
      props: {
        graph_id: 'add_query_graph_line',
        graph_lines: [],
        graph_options: {
          unit: 'first_entry_with_unit',
          explicit_vertical_range: 'auto',
          omit_zero_metrics: true
        },
        metric_backend_available: true,
        create_services_available: true,
        graph_renderer: fakeGraphRenderer
      }
    })

    // Verify the graph lines table is initially empty
    expect(screen.queryAllByRole('row', { name: /^Graph line / }).length).toBe(0)

    // Select metric and attributes
    await selectDropdownOption('Metric name', 'Dummy Metric Name')
    await selectDropdownOption('Resource attributes key', 'Dummy Resource Attribute key')
    await selectDropdownOption('Resource attributes value', 'Dummy Resource Attribute value')
    await selectDropdownOption('Scope attributes key', 'Dummy Scope Attribute key')
    await selectDropdownOption('Scope attributes value', 'Dummy Scope Attribute value')
    await selectDropdownOption('Data point attributes key', 'Dummy Data Point Attribute key')
    await selectDropdownOption('Data point attributes value', 'Dummy Data Point Attribute value')

    // Add the graph line
    const addButton = screen.getByRole('button', { name: 'Add query' })
    await userEvent.click(addButton)

    expect(screen.queryAllByRole('row', { name: /^Graph line / }).length).toBe(1)
    expect(
      screen.getByRole('row', { name: 'Graph line $METRIC_NAME$ - $SERIES_ID$' })
    ).toBeInTheDocument()
  })
})
