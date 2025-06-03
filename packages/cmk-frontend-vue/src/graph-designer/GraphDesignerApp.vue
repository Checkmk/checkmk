<!--
Copyright (C) 2024 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkColorPicker from '@/components/CmkColorPicker.vue'
import CmkSwitch from '@/components/CmkSwitch.vue'
import FixedMetricRowRenderer from '@/graph-designer/components/FixedMetricRowRenderer.vue'
import FormEdit from '@/form/components/FormEdit.vue'
import FormLineType from '@/graph-designer/components/FormLineType.vue'
import FormMetricCells, { type Metric } from '@/graph-designer/components/FormMetricCells.vue'
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
import { computed, ref, type Ref } from 'vue'
import {
  convertFromExplicitVerticalRange,
  convertFromUnit,
  convertToExplicitVerticalRange,
  convertToUnit
} from '@/graph-designer/converters'
import {
  type GraphLine,
  type GraphLines,
  type GraphOptions,
  type I18N,
  type Operation,
  type Transformation
} from 'cmk-shared-typing/typescript/graph_designer'
import { type SpecLineType, type Topic } from '@/graph-designer/type_defs'
import { type ValidationMessages } from '@/form'
import useDragging from '@/lib/useDragging'

const props = defineProps<{
  graph_lines: GraphLines
  graph_options: GraphOptions
  i18n: I18N
}>()

// Specs

const dataConsolidationType = ref<'average' | 'min' | 'max'>('max')
const specConsolidationType = makeSingleChoice('', [
  { name: 'average', title: props.i18n.graph_lines.average },
  { name: 'min', title: props.i18n.graph_lines.minimum },
  { name: 'max', title: props.i18n.graph_lines.maximum }
])
const backendValidationConsolidationType: ValidationMessages = []

const dataScalarType = ref<'warn' | 'crit' | 'min' | 'max'>('crit')
const specScalarType = makeSingleChoice('', [
  { name: 'warn', title: props.i18n.graph_lines.warning },
  { name: 'crit', title: props.i18n.graph_lines.critical },
  { name: 'min', title: props.i18n.graph_lines.minimum },
  { name: 'max', title: props.i18n.graph_lines.maximum }
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

const dataUnit = ref(convertToUnit(props.graph_options.unit))
const specUnit = makeCascadingSingleChoice('', [
  {
    name: 'first_entry_with_unit',
    title: props.i18n.graph_options.unit_first_entry_with_unit,
    parameter_form: makeFixedValue(),
    default_value: null
  },
  {
    name: 'custom',
    title: props.i18n.graph_options.unit_custom,
    parameter_form: makeDictionary('', [
      {
        name: 'notation',
        render_only: false,
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
        name: 'precision',
        render_only: false,
        required: true,
        parameter_form: makeDictionary(props.i18n.graph_options.unit_custom_precision, [
          {
            name: 'type',
            render_only: false,
            required: true,
            parameter_form: makeSingleChoice(props.i18n.graph_options.unit_custom_precision_type, [
              {
                name: 'auto',
                title: props.i18n.graph_options.unit_custom_precision_type_auto
              },
              {
                name: 'strict',
                title: props.i18n.graph_options.unit_custom_precision_type_strict
              }
            ]),
            default_value: 'auto',
            group: null
          },
          {
            name: 'digits',
            render_only: false,
            required: true,
            parameter_form: makeFloat(props.i18n.graph_options.unit_custom_precision_digits, ''),
            default_value: 2,
            group: null
          }
        ]),
        default_value: { type: 'auto', digits: 2 },
        group: null
      }
    ]),
    default_value: { notation: ['decimal', ''], precision: { type: 'auto', digits: 2 } }
  }
])
const backendValidationUnit: ValidationMessages = []

const dataExplicitVerticalRange = ref(
  convertToExplicitVerticalRange(props.graph_options.explicit_vertical_range)
)
const specExplicitVerticalRange = makeCascadingSingleChoice('', [
  {
    name: 'auto',
    title: props.i18n.graph_options.explicit_vertical_range_auto,
    parameter_form: makeFixedValue(),
    default_value: null
  },
  {
    name: 'explicit',
    title: props.i18n.graph_options.explicit_vertical_range_explicit,
    parameter_form: makeDictionary('', [
      {
        name: 'lower',
        render_only: false,
        required: true,
        parameter_form: makeFloat(
          props.i18n.graph_options.explicit_vertical_range_explicit_lower,
          ''
        ),
        default_value: 0.0,
        group: null
      },
      {
        name: 'upper',
        render_only: false,
        required: true,
        parameter_form: makeFloat(
          props.i18n.graph_options.explicit_vertical_range_explicit_upper,
          ''
        ),
        default_value: 1.0,
        group: null
      }
    ]),
    default_value: { lower: 0.0, upper: 1.0 }
  }
])
const backendValidationExplicitVerticalRange: ValidationMessages = []

const dataOmitZeroMetrics = ref(props.graph_options.omit_zero_metrics)
const specOmitZeroMetrics = makeBooleanChoice()
const backendValidationOmitZeroMetrics: ValidationMessages = []

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
      { ident: 'explicit_vertical_range', title: props.i18n.topics.explicit_vertical_range },
      {
        ident: 'omit_zero_metrics',
        title: props.i18n.topics.omit_zero_metrics
      }
    ]
  }
]

// Graph lines

function formulaOf(graphLine: GraphLine): string {
  switch (graphLine.type) {
    case 'metric':
    case 'scalar':
    case 'constant':
      return ''
    case 'sum':
      return `${props.i18n.graph_operations.sum} ${props.i18n.graph_lines.of}`
    case 'product':
      return `${props.i18n.graph_operations.product} ${props.i18n.graph_lines.of}`
    case 'difference':
      return `${props.i18n.graph_operations.difference} ${props.i18n.graph_lines.of}`
    case 'fraction':
      return `${props.i18n.graph_operations.fraction} ${props.i18n.graph_lines.of}`
    case 'average':
      return `${props.i18n.graph_operations.average} ${props.i18n.graph_lines.of}`
    case 'minimum':
      return `${props.i18n.graph_operations.minimum} ${props.i18n.graph_lines.of}`
    case 'maximum':
      return `${props.i18n.graph_operations.maximum} ${props.i18n.graph_lines.of}`
    case 'transformation':
      return `${props.i18n.graph_operations.percentile} ${props.i18n.graph_lines.of}`
    default:
      return ''
  }
}

const dataMetric = ref<Metric>({
  hostName: '',
  serviceName: '',
  metricName: ''
})
const dataScalar = ref<Metric>({
  hostName: '',
  serviceName: '',
  metricName: ''
})

let id = 0
const graphLines: Ref<GraphLines> = ref([])
const selectedGraphLines: Ref<GraphLines> = ref([])

function isDissolvable(graphLine: GraphLine) {
  switch (graphLine.type) {
    case 'sum':
    case 'product':
    case 'difference':
    case 'fraction':
    case 'average':
    case 'minimum':
    case 'maximum':
    case 'transformation':
      return true
    default:
      return false
  }
}

function dissolveOperation(graphLine: Operation) {
  const index = graphLines.value.indexOf(graphLine)
  graphLines.value = graphLines.value.filter((l) => l !== graphLine)
  graphLines.value.splice(index, 0, ...graphLine.operands)
}

function dissolveTransformation(graphLine: Transformation) {
  const index = graphLines.value.indexOf(graphLine)
  graphLines.value = graphLines.value.filter((l) => l !== graphLine)
  graphLines.value.splice(index, 0, graphLine.operand)
}

function dissolveGraphLine(graphLine: GraphLine) {
  switch (graphLine.type) {
    case 'sum':
    case 'product':
    case 'difference':
    case 'fraction':
    case 'average':
    case 'minimum':
    case 'maximum':
      dissolveOperation(graphLine)
      break
    case 'transformation':
      dissolveTransformation(graphLine)
      break
  }
}

function generateOperation(graphLine: Operation): Operation {
  const operands: GraphLines = []
  for (const operand of graphLine.operands) {
    operands.push(generateGraphLine(operand))
  }
  return {
    id: id++,
    type: graphLine.type,
    color: graphLine.color,
    title: graphLine.title,
    visible: graphLine.visible,
    line_type: graphLine.line_type,
    mirrored: graphLine.mirrored,
    operands: operands
  }
}

function generateGraphLine(graphLine: GraphLine): GraphLine {
  switch (graphLine.type) {
    case 'metric':
      return {
        id: id++,
        type: graphLine.type,
        color: graphLine.color,
        title: graphLine.title,
        visible: graphLine.visible,
        line_type: graphLine.line_type,
        mirrored: graphLine.mirrored,
        host_name: graphLine.host_name,
        service_name: graphLine.service_name,
        metric_name: graphLine.metric_name,
        consolidation_type: graphLine.consolidation_type
      }
    case 'scalar':
      return {
        id: id++,
        type: graphLine.type,
        color: graphLine.color,
        title: graphLine.title,
        visible: graphLine.visible,
        line_type: graphLine.line_type,
        mirrored: graphLine.mirrored,
        host_name: graphLine.host_name,
        service_name: graphLine.service_name,
        metric_name: graphLine.metric_name,
        scalar_type: graphLine.scalar_type
      }
    case 'constant':
      return {
        id: id++,
        type: graphLine.type,
        color: graphLine.color,
        title: graphLine.title,
        visible: graphLine.visible,
        line_type: graphLine.line_type,
        mirrored: graphLine.mirrored,
        value: graphLine.value
      }
    case 'sum':
    case 'product':
    case 'difference':
    case 'fraction':
    case 'average':
    case 'minimum':
    case 'maximum':
      return generateOperation(graphLine)
    case 'transformation':
      return {
        id: id++,
        type: graphLine.type,
        color: graphLine.color,
        title: graphLine.title,
        visible: graphLine.visible,
        line_type: graphLine.line_type,
        mirrored: graphLine.mirrored,
        percentile: graphLine.percentile,
        operand: generateGraphLine(graphLine.operand)
      }
  }
}

function cloneGraphLine(graphLine: GraphLine) {
  graphLines.value.push(generateGraphLine(graphLine))
}

function deleteGraphLine(graphLine: GraphLine) {
  graphLines.value = graphLines.value.filter((l) => l !== graphLine)
}

function isOperation(graphLine: GraphLine) {
  switch (graphLine.type) {
    case 'sum':
    case 'product':
    case 'difference':
    case 'fraction':
    case 'average':
    case 'minimum':
    case 'maximum':
      return true
    default:
      return false
  }
}

function addMetric() {
  if (
    dataMetric.value.hostName !== '' &&
    dataMetric.value.serviceName !== '' &&
    dataMetric.value.metricName !== ''
  ) {
    // TODO set color, title, ...
    graphLines.value.push({
      id: id++,
      type: 'metric',
      color: '#ff0000',
      title: `${dataMetric.value.hostName} > ${dataMetric.value.serviceName} > ${dataMetric.value.metricName}`,
      visible: true,
      line_type: 'line',
      mirrored: false,
      host_name: dataMetric.value.hostName,
      service_name: dataMetric.value.serviceName,
      metric_name: dataMetric.value.metricName,
      consolidation_type: dataConsolidationType.value
    })
    dataMetric.value = {
      hostName: '',
      serviceName: '',
      metricName: ''
    }
  }
}

function addScalar() {
  if (
    dataScalar.value.hostName !== '' &&
    dataScalar.value.serviceName !== '' &&
    dataScalar.value.metricName !== ''
  ) {
    // TODO set color, title, ...
    graphLines.value.push({
      id: id++,
      type: 'scalar',
      color: '#ff0000',
      title: `${dataScalar.value.hostName} > ${dataScalar.value.serviceName} > ${dataScalar.value.metricName}`,
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

function showSelectedIds(operator: string) {
  return ` (${selectedGraphLines.value.map((l) => `#${l.id}`).join(` ${operator} `)})`
}

function transformationIsApplicable() {
  return Object.keys(selectedGraphLines.value).length === 1
}

function addGraphLineWithSelection(graphLine: GraphLine) {
  const index = Math.min(...selectedGraphLines.value.map((l) => graphLines.value.indexOf(l)))
  graphLines.value = graphLines.value.filter((l) => !selectedGraphLines.value.includes(l))
  graphLines.value.splice(index, 0, graphLine)
  selectedGraphLines.value = []
}

function applySum() {
  // TODO use other attributes from first operand?
  const firstOperand = selectedGraphLines.value[0]
  if (firstOperand) {
    addGraphLineWithSelection({
      id: id++,
      type: 'sum',
      color: firstOperand.color,
      title: `${props.i18n.graph_operations.sum} ${props.i18n.graph_lines.of} ${selectedGraphLines.value.map((l) => l.title).join(', ')}`,
      visible: true,
      line_type: 'line',
      mirrored: false,
      operands: selectedGraphLines.value
    })
  }
}

function applyProduct() {
  // TODO use other attributes from first operand?
  const firstOperand = selectedGraphLines.value[0]
  if (firstOperand) {
    addGraphLineWithSelection({
      id: id++,
      type: 'product',
      color: firstOperand.color,
      title: `${props.i18n.graph_operations.product} ${props.i18n.graph_lines.of} ${selectedGraphLines.value.map((l) => l.title).join(', ')}`,
      visible: true,
      line_type: 'line',
      mirrored: false,
      operands: selectedGraphLines.value
    })
  }
}

function applyDifference() {
  // TODO use other attributes from first operand?
  const firstOperand = selectedGraphLines.value[0]
  if (firstOperand) {
    addGraphLineWithSelection({
      id: id++,
      type: 'difference',
      color: firstOperand.color,
      title: `${props.i18n.graph_operations.difference} ${props.i18n.graph_lines.of} ${selectedGraphLines.value.map((l) => l.title).join(', ')}`,
      visible: true,
      line_type: 'line',
      mirrored: false,
      operands: selectedGraphLines.value
    })
  }
}

function applyFraction() {
  // TODO use other attributes from first operand?
  const firstOperand = selectedGraphLines.value[0]
  if (firstOperand) {
    addGraphLineWithSelection({
      id: id++,
      type: 'fraction',
      color: firstOperand.color,
      title: `${props.i18n.graph_operations.fraction} ${props.i18n.graph_lines.of} ${selectedGraphLines.value.map((l) => l.title).join(', ')}`,
      visible: true,
      line_type: 'line',
      mirrored: false,
      operands: selectedGraphLines.value
    })
  }
}

function applyAverage() {
  // TODO use other attributes from first operand?
  const firstOperand = selectedGraphLines.value[0]
  if (firstOperand) {
    addGraphLineWithSelection({
      id: id++,
      type: 'average',
      color: firstOperand.color,
      title: `${props.i18n.graph_operations.average} ${props.i18n.graph_lines.of} ${selectedGraphLines.value.map((l) => l.title).join(', ')}`,
      visible: true,
      line_type: 'line',
      mirrored: false,
      operands: selectedGraphLines.value
    })
  }
}

function applyMinimum() {
  // TODO use other attributes from first operand?
  const firstOperand = selectedGraphLines.value[0]
  if (firstOperand) {
    addGraphLineWithSelection({
      id: id++,
      type: 'minimum',
      color: firstOperand.color,
      title: `${props.i18n.graph_operations.minimum} ${props.i18n.graph_lines.of} ${selectedGraphLines.value.map((l) => l.title).join(', ')}`,
      visible: true,
      line_type: 'line',
      mirrored: false,
      operands: selectedGraphLines.value
    })
  }
}

function applyMaximum() {
  // TODO use other attributes from first operand?
  const firstOperand = selectedGraphLines.value[0]
  if (firstOperand) {
    addGraphLineWithSelection({
      id: id++,
      type: 'maximum',
      color: firstOperand.color,
      title: `${props.i18n.graph_operations.maximum} ${props.i18n.graph_lines.of} ${selectedGraphLines.value.map((l) => l.title).join(', ')}`,
      visible: true,
      line_type: 'line',
      mirrored: false,
      operands: selectedGraphLines.value
    })
  }
}

function applyTransformation() {
  // TODO use other attributes from operand?
  const selectedGraphLine = selectedGraphLines.value[0]
  if (selectedGraphLine) {
    addGraphLineWithSelection({
      id: id++,
      type: 'transformation',
      color: '#ff0000',
      title: `${props.i18n.graph_operations.percentile} ${props.i18n.graph_lines.of} ${selectedGraphLine.title}`,
      visible: true,
      line_type: 'line',
      mirrored: false,
      percentile: dataTransformation.value,
      operand: selectedGraphLine
    })
  }
}

// Graph lines table

function computeOddEven(index: number) {
  // TODO n-th children
  return index % 2 === 0 ? 'even0' : 'odd0'
}

const { tableRef, dragStart, dragEnd, dragging } = useDragging()

function dragElement(event: DragEvent) {
  const dragReturn = dragging(event)
  if (dragReturn === null) {
    return
  }
  const movedEntry = graphLines.value.splice(dragReturn.draggedIndex, 1)[0]!
  graphLines.value.splice(dragReturn.targetIndex, 0, movedEntry)
}

const graphDesignerContentAsJson = computed(() => {
  return JSON.stringify({
    graph_lines: graphLines.value,
    graph_options: {
      unit: convertFromUnit(dataUnit.value),
      explicit_vertical_range: convertFromExplicitVerticalRange(dataExplicitVerticalRange.value),
      omit_zero_metrics: dataOmitZeroMetrics.value
    }
  })
})
</script>

<template>
  <table ref="tableRef" class="data oddeven graph_designer_metrics">
    <tbody>
      <tr>
        <th class="header_narrow nowrap">#</th>
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
        <td class="narrow nowrap">{{ graphLine.id }}</td>
        <td class="buttons">
          <!-- TODO: use CmkCheckbox building block, see FormCheckboxListChoice how to utilize events!-->
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
            v-if="isDissolvable(graphLine)"
            :title="props.i18n.graph_lines.dissolve_operation"
            src="themes/facelift/images/icon_dissolve_operation.png"
            class="icon iconbutton png"
            @click="dissolveGraphLine(graphLine)"
          />
          <img
            :title="props.i18n.graph_lines.clone_this_entry"
            src="themes/facelift/images/icon_clone.svg"
            class="icon iconbutton"
            @click="cloneGraphLine(graphLine)"
          />
          <img
            :title="props.i18n.graph_lines.move_this_entry"
            src="themes/modern-dark/images/icon_drag.svg"
            class="icon iconbutton"
            @dragstart="dragStart"
            @drag="dragElement"
            @dragend="dragEnd"
          />
          <img
            :title="props.i18n.graph_lines.delete_this_entry"
            src="themes/facelift/images/icon_delete.svg"
            class="icon iconbutton"
            @click="deleteGraphLine(graphLine)"
          />
        </td>
        <td class="narrow"><CmkColorPicker v-model:data="graphLine.color" /></td>
        <td class="nobr narrow"><FormTitle v-model:data="graphLine.title" /></td>
        <td class="buttons"><CmkSwitch v-model:data="graphLine.visible" /></td>
        <td class="narrow">
          <FormLineType v-model:data="graphLine.line_type" :spec="specLineType" />
        </td>
        <td class="buttons"><CmkSwitch v-model:data="graphLine.mirrored" /></td>
        <td>
          <div v-if="graphLine.type === 'metric'">
            <FixedMetricRowRenderer>
              <template #metric_type>
                <FormEdit
                  v-model:data="graphLine.consolidation_type"
                  :spec="specConsolidationType"
                  :backend-validation="backendValidationConsolidationType"
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
          <div v-else-if="graphLine.type === 'scalar'">
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
          <div v-else-if="graphLine.type === 'transformation'">
            {{ formulaOf(graphLine) }}
            <br />
            <div
              :style="{
                'background-color': graphLine.operand.color,
                'border-color': graphLine.operand.color
              }"
              class="color"
            ></div>
            {{ graphLine.operand.title }}
          </div>
          <div v-else-if="isOperation(graphLine)">
            {{ formulaOf(graphLine) }}
            <div v-for="operand in graphLine.operands" :key="operand.id">
              <div
                :style="{ 'background-color': operand.color, 'border-color': operand.color }"
                class="color"
              ></div>
              {{ operand.title }}
            </div>
          </div>
        </td>
      </tr>
    </tbody>
  </table>

  <TopicsRenderer :topics="topics">
    <template #metric>
      <div>
        <MetricRowRenderer>
          <template #metric_cells>
            <FormMetricCells v-model:data="dataMetric" />
          </template>
          <template #metric_type>
            <FormEdit
              v-model:data="dataConsolidationType"
              :spec="specConsolidationType"
              :backend-validation="backendValidationConsolidationType"
            />
          </template>
          <template #metric_action>
            <button @click.prevent="addMetric">
              <img
                :title="props.i18n.graph_lines.add"
                src="themes/facelift/images/icon_new.svg"
                class="icon iconbutton"
              />
              {{ props.i18n.graph_lines.add }}
            </button>
          </template>
        </MetricRowRenderer>
      </div>
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
            <button @click.prevent="addScalar">
              <img
                :title="props.i18n.graph_lines.add"
                src="themes/facelift/images/icon_new.svg"
                class="icon iconbutton"
              />
              {{ props.i18n.graph_lines.add }}
            </button>
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
        <button @click.prevent="addConstant">
          <img
            :title="props.i18n.graph_lines.add"
            src="themes/facelift/images/icon_new.svg"
            class="icon iconbutton"
          />
          {{ props.i18n.graph_lines.add }}
        </button>
      </div>
    </template>
    <template #operations>
      <div v-if="operationIsApplicable()">
        <button @click="applySum">{{ props.i18n.graph_operations.sum }}</button>
        <button @click="applyProduct">{{ props.i18n.graph_operations.product }}</button>
        <button @click="applyDifference">
          {{ props.i18n.graph_operations.difference }} {{ showSelectedIds('-') }}
        </button>
        <button @click="applyFraction">
          {{ props.i18n.graph_operations.fraction }} {{ showSelectedIds('/') }}
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
    <template #explicit_vertical_range>
      <div>
        <FormEdit
          v-model:data="dataExplicitVerticalRange"
          :spec="specExplicitVerticalRange"
          :backend-validation="backendValidationExplicitVerticalRange"
        />
      </div>
    </template>
    <template #omit_zero_metrics>
      <div>
        <FormEdit
          v-model:data="dataOmitZeroMetrics"
          :spec="specOmitZeroMetrics"
          :backend-validation="backendValidationOmitZeroMetrics"
        />
      </div>
    </template>
  </TopicsRenderer>

  <!-- This input field contains the computed json value which is sent when the form is submitted -->
  <input v-model="graphDesignerContentAsJson" name="graph_designer_content" type="hidden" />
</template>
