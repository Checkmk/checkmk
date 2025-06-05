/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import GraphDesignerApp from '@/graph-designer/GraphDesignerApp.vue'

test('Render GraphDesignerApp', () => {
  render(GraphDesignerApp, {
    props: {
      graph_lines: [],
      graph_options: {
        unit: 'first_entry_with_unit',
        explicit_vertical_range: 'auto',
        omit_zero_metrics: true
      },
      i18n: {
        graph_lines: {
          of: 'of',
          average: 'average',
          warning: 'warning',
          critical: 'critical',
          minimum: 'minimum',
          maximum: 'maximum',
          actions: 'actions',
          color: 'color',
          auto_title: 'title',
          custom_title: 'custom title',
          visible: 'visible',
          line_style: 'line_style',
          line: 'line',
          area: 'area',
          stack: 'stack',
          mirrored: 'mirrored',
          formula: 'formula',
          dissolve_operation: 'dissolve_operation',
          clone_this_entry: 'clone_this_entry',
          move_this_entry: 'move_this_entry',
          delete_this_entry: 'delete_this_entry',
          add: 'add'
        },
        graph_operations: {
          sum: 'sum',
          product: 'product',
          difference: 'difference',
          fraction: 'fraction',
          average: 'average',
          minimum: 'minimum',
          maximum: 'maximum',
          no_selected_graph_lines: 'no_selected_graph_lines',
          percentile: 'percentile',
          apply: 'apply',
          no_selected_graph_line: 'no_selected_graph_line'
        },
        graph_options: {
          unit_first_entry_with_unit: 'unit_first_entry_with_unit',
          unit_custom: 'unit_custom',
          unit_custom_notation: 'unit_custom_notation',
          unit_custom_notation_symbol: 'unit_custom_notation_symbol',
          unit_custom_notation_decimal: 'unit_custom_notation_decimal',
          unit_custom_notation_si: 'unit_custom_notation_si',
          unit_custom_notation_iec: 'unit_custom_notation_iec',
          unit_custom_notation_standard_scientific: 'unit_custom_notation_standard_scientific',
          unit_custom_notation_engineering_scientific:
            'unit_custom_notation_engineering_scientific',
          unit_custom_notation_time: 'unit_custom_notation_time',
          unit_custom_precision: 'unit_custom_precision',
          unit_custom_precision_type: 'unit_custom_precision_type',
          unit_custom_precision_type_auto: 'unit_custom_precision_type_auto',
          unit_custom_precision_type_strict: 'unit_custom_precision_type_strict',
          unit_custom_precision_digits: 'unit_custom_precision_digits',
          explicit_vertical_range_auto: 'explicit_vertical_range_auto',
          explicit_vertical_range_explicit: 'explicit_vertical_range_explicit',
          explicit_vertical_range_explicit_lower: 'explicit_vertical_range_explicit_lower',
          explicit_vertical_range_explicit_upper: 'explicit_vertical_range_explicit_upper'
        },
        topics: {
          metric: 'metric',
          scalar: 'scalar',
          constant: 'constant',
          graph_lines: 'graph_lines',
          operations: 'operations',
          transformation: 'transformation',
          graph_operations: 'graph_operations',
          unit: 'unit',
          explicit_vertical_range: 'explicit_vertical_range',
          omit_zero_metrics: 'omit_zero_metrics',
          graph_options: 'graph_options'
        }
      }
    }
  })
})
