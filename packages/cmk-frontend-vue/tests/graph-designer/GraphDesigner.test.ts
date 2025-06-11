/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import { render } from '@testing-library/vue'
import { type GraphLines, type GraphOptions } from 'cmk-shared-typing/typescript/graph_designer'
import GraphDesignerApp from '@/graph-designer/GraphDesignerApp.vue'

function fakeGraphRenderer(
  graph_id: string,
  graph_lines: GraphLines,
  graph_options: GraphOptions,
  container: HTMLDivElement
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
      i18n: {
        actions: 'actions',
        add: 'add',
        apply: 'apply',
        area: 'area',
        auto_title: 'title',
        average: 'average',
        clone_this_entry: 'clone_this_entry',
        color: 'color',
        constant: 'constant',
        critical: 'critical',
        custom_title: 'custom title',
        delete_this_entry: 'delete_this_entry',
        difference: 'difference',
        dissolve_operation: 'dissolve_operation',
        explicit_vertical_range: 'explicit_vertical_range',
        explicit_vertical_range_auto: 'explicit_vertical_range_auto',
        explicit_vertical_range_explicit: 'explicit_vertical_range_explicit',
        explicit_vertical_range_explicit_lower: 'explicit_vertical_range_explicit_lower',
        explicit_vertical_range_explicit_upper: 'explicit_vertical_range_explicit_upper',
        formula: 'formula',
        fraction: 'fraction',
        graph_lines: 'graph_lines',
        graph_operations: 'graph_operations',
        graph_options: 'graph_options',
        line: 'line',
        line_style: 'line_style',
        maximum: 'maximum',
        metric: 'metric',
        minimum: 'minimum',
        mirrored: 'mirrored',
        move_this_entry: 'move_this_entry',
        no_selected_graph_line: 'no_selected_graph_line',
        no_selected_graph_lines: 'no_selected_graph_lines',
        of: 'of',
        omit_zero_metrics: 'omit_zero_metrics',
        operations: 'operations',
        percentile: 'percentile',
        placeholder_host_name: 'host name',
        placeholder_metric_name: 'metric name',
        placeholder_service_name: 'service name',
        product: 'product',
        scalar: 'scalar',
        stack: 'stack',
        sum: 'sum',
        transformation: 'transformation',
        unit: 'unit',
        unit_custom: 'unit_custom',
        unit_custom_notation: 'unit_custom_notation',
        unit_custom_notation_decimal: 'unit_custom_notation_decimal',
        unit_custom_notation_engineering_scientific: 'unit_custom_notation_engineering_scientific',
        unit_custom_notation_iec: 'unit_custom_notation_iec',
        unit_custom_notation_si: 'unit_custom_notation_si',
        unit_custom_notation_standard_scientific: 'unit_custom_notation_standard_scientific',
        unit_custom_notation_symbol: 'unit_custom_notation_symbol',
        unit_custom_notation_time: 'unit_custom_notation_time',
        unit_custom_precision: 'unit_custom_precision',
        unit_custom_precision_digits: 'unit_custom_precision_digits',
        unit_custom_precision_type: 'unit_custom_precision_type',
        unit_custom_precision_type_auto: 'unit_custom_precision_type_auto',
        unit_custom_precision_type_strict: 'unit_custom_precision_type_strict',
        unit_first_entry_with_unit: 'unit_first_entry_with_unit',
        visible: 'visible',
        warning: 'warning'
      },
      graph_renderer: fakeGraphRenderer
    }
  })
})
