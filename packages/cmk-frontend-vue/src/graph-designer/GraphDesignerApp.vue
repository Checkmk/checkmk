<!--
Copyright (C) 2024 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import FixedMetricRowRenderer from '@/graph-designer/components/FixedMetricRowRenderer.vue'
import FormColorPicker from '@/graph-designer/components/FormColorPicker.vue'
import FormEdit from '@/form/components/FormEdit.vue'
import FormLineType from '@/graph-designer/components/FormLineType.vue'
import FormMetricCells, { type Metric } from '@/graph-designer/components/FormMetricCells.vue'
import FormSwitch from '@/graph-designer/components/FormSwitch.vue'
import FormTitle from '@/graph-designer/components/FormTitle.vue'
import MetricRowRenderer from '@/graph-designer/components/MetricRowRenderer.vue'
import TopicsRenderer from '@/graph-designer/components/TopicsRenderer.vue'
import {
  makeBooleanChoice,
  makeCascadingSingleChoice,
  makeDictionary,
  makeFixedValue,
  makeFloat,
  makeSingleChoice,
  makeString
} from '@/graph-designer/specs'
import { ref, type Ref } from 'vue'
import { type I18N, type GraphLines } from '@/graph-designer/type_defs'
import { type SpecLineType, type Topic } from '@/graph-designer/components/type_defs'
import { type ValidationMessages } from '@/form'

const props = defineProps<{
  graph_lines: GraphLines
  i18n: I18N
}>()

// Specs

const dataScalarType = ref<'warning' | 'critical' | 'minimum' | 'maximum'>('critical')
const specScalarType = makeSingleChoice('', [
  { name: 'warning', title: props.i18n.graph_lines.warning },
  { name: 'critical', title: props.i18n.graph_lines.critical },
  { name: 'minimum', title: props.i18n.graph_lines.minimum },
  { name: 'maximum', title: props.i18n.graph_lines.maximum }
])
const backendValidationScalarType: ValidationMessages = []

const dataConstant = ref(1)
const specConstant = makeFloat('', '')
const backendValidationConstant: ValidationMessages = []

const specLineType: SpecLineType = {
  line: props.i18n.graph_lines.line,
  area: props.i18n.graph_lines.area,
  stack: props.i18n.graph_lines.stack
}

const dataTransformation = ref(95)
const specTransformation = makeFloat('', props.i18n.graph_operations.percentile)
const backendValidationTransformation: ValidationMessages = []

const dataUnit = ref(['first_with_unit', null])
const specUnit = makeCascadingSingleChoice('', [
  {
    name: 'first_with_unit',
    title: props.i18n.graph_options.unit_first_with_unit,
    parameter_form: makeFixedValue(),
    default_value: null
  },
  {
    name: 'custom',
    title: props.i18n.graph_options.unit_custom,
    parameter_form: makeDictionary('', [
      {
        ident: 'notation',
        required: true,
        parameter_form: makeCascadingSingleChoice(props.i18n.graph_options.unit_custom_notation, [
          {
            name: 'decimal',
            title: props.i18n.graph_options.unit_custom_notation_decimal,
            parameter_form: makeString(
              props.i18n.graph_options.unit_custom_notation_symbol,
              'symbol',
              null
            ),
            default_value: ''
          },
          {
            name: 'si',
            title: props.i18n.graph_options.unit_custom_notation_si,
            parameter_form: makeString(
              props.i18n.graph_options.unit_custom_notation_symbol,
              'symbol',
              null
            ),
            default_value: ''
          },
          {
            name: 'iec',
            title: props.i18n.graph_options.unit_custom_notation_iec,
            parameter_form: makeString(
              props.i18n.graph_options.unit_custom_notation_symbol,
              'symbol',
              null
            ),
            default_value: ''
          },
          {
            name: 'standard_scientific',
            title: props.i18n.graph_options.unit_custom_notation_standard_scientific,
            parameter_form: makeString(
              props.i18n.graph_options.unit_custom_notation_symbol,
              'symbol',
              null
            ),
            default_value: ''
          },
          {
            name: 'engineering_scientific',
            title: props.i18n.graph_options.unit_custom_notation_engineering_scientific,
            parameter_form: makeString(
              props.i18n.graph_options.unit_custom_notation_symbol,
              'symbol',
              null
            ),
            default_value: ''
          },
          {
            name: 'time',
            title: props.i18n.graph_options.unit_custom_notation_time,
            parameter_form: makeFixedValue(),
            default_value: null
          }
        ]),
        default_value: { notation: ['decimal', null] },
        group: null
      },
      {
        ident: 'precision',
        required: true,
        parameter_form: makeDictionary(props.i18n.graph_options.unit_custom_precision, [
          {
            ident: 'rounding_mode',
            required: true,
            parameter_form: makeSingleChoice(
              props.i18n.graph_options.unit_custom_precision_rounding_mode,
              [
                {
                  name: 'auto',
                  title: props.i18n.graph_options.unit_custom_precision_rounding_mode_auto
                },
                {
                  name: 'strict',
                  title: props.i18n.graph_options.unit_custom_precision_rounding_mode_strict
                }
              ]
            ),
            default_value: 'auto',
            group: null
          },
          {
            ident: 'digits',
            required: true,
            parameter_form: makeFloat(props.i18n.graph_options.unit_custom_precision_digits, ''),
            default_value: 2,
            group: null
          }
        ]),
        default_value: { rounding_mode: 'auto', digits: 2 },
        group: null
      }
    ]),
    default_value: { notation: ['decimal', ''], precision: { rounding_mode: 'auto', digits: 2 } }
  }
])
const backendValidationUnit: ValidationMessages = []

const dataVerticalRange = ref(['auto', null])
const specVerticalRange = makeCascadingSingleChoice('', [
  {
    name: 'auto',
    title: props.i18n.graph_options.vertical_range_auto,
    parameter_form: makeFixedValue(),
    default_value: null
  },
  {
    name: 'explicit',
    title: props.i18n.graph_options.vertical_range_explicit,
    parameter_form: makeDictionary('', [
      {
        ident: 'lower',
        required: true,
        parameter_form: makeFloat(props.i18n.graph_options.vertical_range_explicit_lower, ''),
        default_value: 0.0,
        group: null
      },
      {
        ident: 'upper',
        required: true,
        parameter_form: makeFloat(props.i18n.graph_options.vertical_range_explicit_upper, ''),
        default_value: 1.0,
        group: null
      }
    ]),
    default_value: { lower: 0.0, upper: 1.0 }
  }
])
const backendValidationVerticalRange: ValidationMessages = []

const dataMetricsWithZeroValues = ref(true)
const specMetricsWithZeroValues = makeBooleanChoice()
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

const dataScalar = ref<Metric>({
  hostName: '',
  serviceName: '',
  metricName: ''
})

let id = 0
const graphLines: Ref<GraphLines> = ref([])
const selectedGraphLines: Ref<GraphLines> = ref([])

function isDissolvable() {
  return false
}

function addMetric() {}

function addScalar() {
  if (
    dataScalar.value.hostName !== '' &&
    dataScalar.value.serviceName !== '' &&
    dataScalar.value.metricName !== ''
  ) {
    // TODO set color, title, ...
    const scalarType = specScalarType['elements'].find((e) => e.name === dataScalarType.value)
    const scalarTypeTitle = scalarType ? scalarType.title : ''
    graphLines.value.push({
      id: id++,
      type: 'scalar',
      color: '#ff0000',
      title: `${dataScalar.value.hostName} > ${dataScalar.value.serviceName} > ${dataScalar.value.metricName}`,
      title_short: `${scalarTypeTitle} ${props.i18n.graph_lines.of} ${dataScalar.value.metricName}`,
      visible: true,
      line_type: 'line',
      mirrored: false,
      host_name: dataScalar.value.hostName,
      service_name: dataScalar.value.serviceName,
      metric_name: dataScalar.value.metricName,
      scalar_type: dataScalarType.value
    })
    dataScalar.value = {
      hostName: '',
      serviceName: '',
      metricName: ''
    }
  }
}

function addConstant() {
  graphLines.value.push({
    id: id++,
    type: 'constant',
    color: '#ff0000',
    title: `${props.i18n.topics.constant} ${dataConstant.value}`,
    title_short: props.i18n.topics.constant,
    visible: true,
    line_type: 'line',
    mirrored: false,
    value: dataConstant.value
  })
  dataConstant.value = 1
}

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
        <td class="narrow"><FormColorPicker v-model:data-color="graphLine.color" /></td>
        <td class="nobr narrow"><FormTitle v-model:data-title="graphLine.title" /></td>
        <td class="buttons"><FormSwitch v-model:data-switch="graphLine.visible" /></td>
        <td class="narrow">
          <FormLineType v-model:data-line-type="graphLine.line_type" :spec="specLineType" />
        </td>
        <td class="buttons"><FormSwitch v-model:data-switch="graphLine.mirrored" /></td>
        <td>
          <div v-if="graphLine.type === 'scalar'">
            <FixedMetricRowRenderer>
              <template #metric_type>
                <FormEdit
                  v-model:data="graphLine.scalar_type"
                  :spec="specScalarType"
                  :backend-validation="backendValidationScalarType"
                />
              </template>
              <template #metric_of>
                {{ props.i18n.graph_lines.of }}
              </template>
              <template #metric_title>
                {{ graphLine.title }}
              </template>
            </FixedMetricRowRenderer>
          </div>
          <div v-else-if="graphLine.type === 'constant'">
            {{ graphLine.title }}
          </div>
        </td>
      </tr>
    </tbody>
  </table>

  <TopicsRenderer :topics="topics">
    <template #metric>
      <button @click="addMetric">{{ props.i18n.graph_lines.add }}</button>
    </template>
    <template #scalar>
      <div>
        <MetricRowRenderer>
          <template #metric_cells>
            <FormMetricCells v-model:data="dataScalar" />
          </template>
          <template #metric_type>
            <FormEdit
              v-model:data="dataScalarType"
              :spec="specScalarType"
              :backend-validation="backendValidationScalarType"
            />
          </template>
          <template #metric_action>
            <button @click="addScalar">{{ props.i18n.graph_lines.add }}</button>
          </template>
        </MetricRowRenderer>
      </div>
    </template>
    <template #constant>
      <div>
        <FormEdit
          v-model:data="dataConstant"
          :spec="specConstant"
          :backend-validation="backendValidationConstant"
        />
        <button @click="addConstant">{{ props.i18n.graph_lines.add }}</button>
      </div>
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
