/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
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

  const dissolveButton = screen.getByRole('img', { name: 'Dissolve operation' })
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

  const addRuleButton = screen.getByRole('img', { name: 'Add rule: Metric backend (Custom query)' })
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

    const addRuleButton = screen.queryByRole('img', {
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
