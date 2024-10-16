<!--
Copyright (C) 2024 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import FormColorPicker from '@/graph-designer/components/FormColorPicker.vue'
import FormEdit from '@/form/components/FormEdit.vue'
import FormLineType from '@/graph-designer/components/FormLineType.vue'
import FormSwitch from '@/graph-designer/components/FormSwitch.vue'
import FormTitle from '@/graph-designer/components/FormTitle.vue'
import TopicsRenderer from '@/graph-designer/components/TopicsRenderer.vue'
import { ref, type Ref } from 'vue'
import { type I18N, type GraphLines } from '@/graph-designer/type_defs'
import { type SpecLineType, type Topic } from '@/graph-designer/components/type_defs'
import { type ValidationMessages } from '@/form'

const props = defineProps<{
  graph_lines: GraphLines
  i18n: I18N
}>()

// Specs

const specLineType: SpecLineType = {
  line: props.i18n.graph_lines.line,
  area: props.i18n.graph_lines.area,
  stack: props.i18n.graph_lines.stack
}

const dataTransformation = ref(95)
const specTransformation = {
  type: 'float',
  title: '',
  help: '',
  validators: [],
  label: props.i18n.graph_operations.percentile
}
const backendValidationTransformation: ValidationMessages = []

const dataUnit = ref(['first_with_unit', null])
const specUnit = {
  type: 'cascading_single_choice',
  title: '',
  help: '',
  validators: [],
  elements: [
    {
      name: 'first_with_unit',
      title: props.i18n.graph_options.unit_first_with_unit,
      parameter_form: {
        type: 'fixed_value',
        title: '',
        help: '',
        validators: []
      },
      default_value: null
    },
    {
      name: 'custom',
      title: props.i18n.graph_options.unit_custom,
      parameter_form: {
        type: 'dictionary',
        title: '',
        help: '',
        validators: [],
        elements: [
          {
            ident: 'notation',
            required: true,
            parameter_form: {
              type: 'cascading_single_choice',
              title: props.i18n.graph_options.unit_custom_notation,
              help: '',
              validators: [],
              elements: [
                {
                  name: 'decimal',
                  title: props.i18n.graph_options.unit_custom_notation_decimal,
                  parameter_form: {
                    type: 'string',
                    title: props.i18n.graph_options.unit_custom_notation_symbol,
                    help: '',
                    validators: [],
                    input_hint: 'symbol',
                    field_size: 'SMALL'
                  },
                  default_value: ''
                },
                {
                  name: 'si',
                  title: props.i18n.graph_options.unit_custom_notation_si,
                  parameter_form: {
                    type: 'string',
                    title: props.i18n.graph_options.unit_custom_notation_symbol,
                    help: '',
                    validators: [],
                    input_hint: 'symbol',
                    field_size: 'SMALL'
                  },
                  default_value: ''
                },
                {
                  name: 'iec',
                  title: props.i18n.graph_options.unit_custom_notation_iec,
                  parameter_form: {
                    type: 'string',
                    title: props.i18n.graph_options.unit_custom_notation_symbol,
                    help: '',
                    validators: [],
                    input_hint: 'symbol',
                    field_size: 'SMALL'
                  },
                  default_value: ''
                },
                {
                  name: 'standard_scientific',
                  title: props.i18n.graph_options.unit_custom_notation_standard_scientific,
                  parameter_form: {
                    type: 'string',
                    title: props.i18n.graph_options.unit_custom_notation_symbol,
                    help: '',
                    validators: [],
                    input_hint: 'symbol',
                    field_size: 'SMALL'
                  },
                  default_value: ''
                },
                {
                  name: 'engineering_scientific',
                  title: props.i18n.graph_options.unit_custom_notation_engineering_scientific,
                  parameter_form: {
                    type: 'string',
                    title: props.i18n.graph_options.unit_custom_notation_symbol,
                    help: '',
                    validators: [],
                    input_hint: 'symbol',
                    field_size: 'SMALL'
                  },
                  default_value: ''
                },
                {
                  name: 'time',
                  title: props.i18n.graph_options.unit_custom_notation_time,
                  parameter_form: {
                    type: 'fixed_value',
                    title: '',
                    help: '',
                    validators: []
                  },
                  default_value: null
                }
              ]
            },
            default_value: { decimal: '' }
          },
          {
            ident: 'precision',
            required: true,
            parameter_form: {
              type: 'dictionary',
              title: props.i18n.graph_options.unit_custom_precision,
              help: '',
              validators: [],
              elements: [
                {
                  ident: 'rounding_mode',
                  required: true,
                  parameter_form: {
                    type: 'single_choice',
                    title: props.i18n.graph_options.unit_custom_precision_rounding_mode,
                    help: '',
                    validators: [],
                    elements: [
                      {
                        name: 'auto',
                        title: props.i18n.graph_options.unit_custom_precision_rounding_mode_auto
                      },
                      {
                        name: 'strict',
                        title: props.i18n.graph_options.unit_custom_precision_rounding_mode_strict
                      }
                    ],
                    frozen: false
                  },
                  default_value: 'auto'
                },
                {
                  ident: 'digits',
                  required: true,
                  parameter_form: {
                    type: 'float',
                    title: props.i18n.graph_options.unit_custom_precision_digits,
                    help: '',
                    validators: []
                  },
                  default_value: 2
                }
              ]
            },
            default_value: { rounding_mode: 'auto', digits: 2 }
          }
        ]
      },
      default_value: { notation: ['decimal', ''], precision: { rounding_mode: 'auto', digits: 2 } }
    }
  ]
}
const backendValidationUnit: ValidationMessages = []

const dataVerticalRange = ref(['auto', null])
const specVerticalRange = {
  type: 'cascading_single_choice',
  title: '',
  help: '',
  validators: [],
  elements: [
    {
      name: 'auto',
      title: props.i18n.graph_options.vertical_range_auto,
      parameter_form: {
        type: 'fixed_value',
        title: 'i18n:Title',
        help: '',
        validators: []
      }
    },
    {
      name: 'explicit',
      title: props.i18n.graph_options.vertical_range_explicit,
      parameter_form: {
        type: 'dictionary',
        title: '',
        help: '',
        validators: [],
        elements: [
          {
            ident: 'lower',
            required: true,
            parameter_form: {
              type: 'float',
              title: props.i18n.graph_options.vertical_range_explicit_lower,
              help: '',
              validators: []
            },
            default_value: 0.0
          },
          {
            ident: 'upper',
            required: true,
            parameter_form: {
              type: 'float',
              title: props.i18n.graph_options.vertical_range_explicit_upper,
              help: '',
              validators: []
            },
            default_value: 1.0
          }
        ]
      },
      default_value: { lower: 0.0, upper: 1.0 }
    }
  ]
}
const backendValidationVerticalRange: ValidationMessages = []

const dataMetricsWithZeroValues = ref(true)
const specMetricsWithZeroValues = {
  type: 'boolean_choice',
  title: '',
  help: '',
  validators: []
}
const backendValidationMetricsWithZeroValues: ValidationMessages = []

const topics: Topic[] = [
  {
    ident: 'graph_lines',
    title: props.i18n.topics.graph_lines,
    elements: [
      { ident: 'metric', title: props.i18n.topics.metric },
      { ident: 'scalar', title: props.i18n.topics.scalar },
      { ident: 'constant', title: props.i18n.topics.constant }
    ]
  },
  {
    ident: 'graph_operations',
    title: props.i18n.topics.graph_operations,
    elements: [
      { ident: 'operations', title: props.i18n.topics.operations },
      { ident: 'transformation', title: props.i18n.topics.transformation }
    ]
  },
  {
    ident: 'graph_options',
    title: props.i18n.topics.graph_options,
    elements: [
      { ident: 'unit', title: props.i18n.topics.unit },
      { ident: 'vertical_range', title: props.i18n.topics.vertical_range },
      {
        ident: 'metrics_with_zero_values',
        title: props.i18n.topics.metrics_with_zero_values
      }
    ]
  }
]

// Graph lines

const graphLines: Ref<GraphLines> = ref([])
const selectedGraphLines: Ref<GraphLines> = ref([])

function isDissolvable() {
  return false
}

function addMetric() {}

function addScalar() {}

function addConstant() {}

// Operations on selected graph lines

function operationIsApplicable() {
  return Object.keys(selectedGraphLines.value).length >= 2
}

function binaryOperationIsApplicable() {
  return Object.keys(selectedGraphLines.value).length === 2
}

function transformationIsApplicable() {
  return Object.keys(selectedGraphLines.value).length === 1
}

function applySum() {}

function applyProduct() {}

function applyDifference() {}

function applyFraction() {}

function applyAverage() {}

function applyMinimum() {}

function applyMaximum() {}

function applyTransformation() {}

// Graph lines table

function computeOddEven(index: number) {
  // TODO n-th children
  return index % 2 === 0 ? 'even0' : 'odd0'
}
</script>

<template>
  <table class="data oddeven graph_designer_metrics">
    <tbody>
      <tr>
        <th class="header_buttons"></th>
        <th class="header_buttons">{{ props.i18n.graph_lines.actions }}</th>
        <th class="header_narrow">{{ props.i18n.graph_lines.color }}</th>
        <th class="header_nobr narrow">{{ props.i18n.graph_lines.title }}</th>
        <th class="header_buttons">{{ props.i18n.graph_lines.visible }}</th>
        <th class="header_narrow">{{ props.i18n.graph_lines.line_style }}</th>
        <th class="header_buttons">{{ props.i18n.graph_lines.mirrored }}</th>
        <th>{{ props.i18n.graph_lines.formula }}</th>
      </tr>
      <tr
        v-for="(graphLine, index) in graphLines"
        :key="graphLine.id"
        class="data"
        :class="computeOddEven(index)"
      >
        <td class="buttons">
          <input
            :id="graphLine.id.toString()"
            v-model="selectedGraphLines"
            :value="graphLine"
            type="checkbox"
            class="checkbox"
          />
          <label :for="graphLine.id.toString()"></label>
        </td>
        <td class="buttons">
          <img
            v-if="isDissolvable()"
            :title="props.i18n.graph_lines.dissolve_operation"
            src="themes/facelift/images/icon_dissolve_operation.png"
            class="icon iconbutton png"
          />
          <img
            :title="props.i18n.graph_lines.clone_this_entry"
            src="themes/facelift/images/icon_clone.svg"
            class="icon iconbutton"
          />
          <img
            :title="props.i18n.graph_lines.move_this_entry"
            src="themes/modern-dark/images/icon_drag.svg"
            class="icon iconbutton"
          />
          <img
            :title="props.i18n.graph_lines.delete_this_entry"
            src="themes/facelift/images/icon_delete.svg"
            class="icon iconbutton"
          />
        </td>
        <td class="narrow"><FormColorPicker v-model:dataColor="graphLine.color" /></td>
        <td class="nobr narrow"><FormTitle v-model:dataTitle="graphLine.title" /></td>
        <td class="buttons"><FormSwitch v-model:dataSwitch="graphLine.visible" /></td>
        <td class="narrow">
          <FormLineType v-model:dataLineType="graphLine.line_type" :spec="specLineType" />
        </td>
        <td class="buttons"><FormSwitch v-model:dataSwitch="graphLine.mirrored" /></td>
        <td></td>
      </tr>
    </tbody>
  </table>

  <TopicsRenderer :topics="topics">
    <template #metric>
      <button @click="addMetric">{{ props.i18n.graph_lines.add }}</button>
    </template>
    <template #scalar>
      <button @click="addScalar">{{ props.i18n.graph_lines.add }}</button>
    </template>
    <template #constant>
      <button @click="addConstant">{{ props.i18n.graph_lines.add }}</button>
    </template>
    <template #operations>
      <div v-if="operationIsApplicable()">
        <button @click="applySum">{{ props.i18n.graph_operations.sum }}</button>
        <button @click="applyProduct">{{ props.i18n.graph_operations.product }}</button>
        <button v-if="binaryOperationIsApplicable()" @click="applyDifference">
          {{ props.i18n.graph_operations.difference }}
        </button>
        <button v-if="binaryOperationIsApplicable()" @click="applyFraction">
          {{ props.i18n.graph_operations.fraction }}
        </button>
        <button @click="applyAverage">{{ props.i18n.graph_operations.average }}</button>
        <button @click="applyMinimum">{{ props.i18n.graph_operations.minimum }}</button>
        <button @click="applyMaximum">{{ props.i18n.graph_operations.maximum }}</button>
      </div>
      <div v-else>{{ props.i18n.graph_operations.no_selected_graph_lines }}</div>
    </template>
    <template #transformation>
      <div v-if="transformationIsApplicable()">
        <FormEdit
          v-model:data="dataTransformation"
          :spec="specTransformation"
          :backend-validation="backendValidationTransformation"
        />
        <button @click="applyTransformation">{{ props.i18n.graph_operations.apply }}</button>
      </div>
      <div v-else>{{ props.i18n.graph_operations.no_selected_graph_line }}</div>
    </template>
    <template #unit>
      <div>
        <FormEdit
          v-model:data="dataUnit"
          :spec="specUnit"
          :backend-validation="backendValidationUnit"
        />
      </div>
    </template>
    <template #vertical_range>
      <div>
        <FormEdit
          v-model:data="dataVerticalRange"
          :spec="specVerticalRange"
          :backend-validation="backendValidationVerticalRange"
        />
      </div>
    </template>
    <template #metrics_with_zero_values>
      <div>
        <FormEdit
          v-model:data="dataMetricsWithZeroValues"
          :spec="specMetricsWithZeroValues"
          :backend-validation="backendValidationMetricsWithZeroValues"
        />
      </div>
    </template>
  </TopicsRenderer>
</template>
