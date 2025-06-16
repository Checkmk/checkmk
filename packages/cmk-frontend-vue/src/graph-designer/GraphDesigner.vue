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
import { computed, onMounted, onBeforeUnmount, ref, type Ref, watch } from 'vue'
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
import { fetchMetricColor } from '@/graph-designer/fetch_metric_color'
import { type GraphRenderer } from '@/graph-designer/graph'

const props = defineProps<{
  graph_id: string
  graph_lines: GraphLines
  graph_options: GraphOptions
  i18n: I18N
  graph_renderer: GraphRenderer
}>()

const preventLeaving = ref(false)

const handleBrowserDialog = (event: BeforeUnloadEvent) => {
  if (preventLeaving.value) {
    event.preventDefault()
    event.returnValue = ''
  }
}

const handlePreventLeaving = (prevent: boolean) => {
  preventLeaving.value = prevent
  if (prevent) {
    window.addEventListener('beforeunload', handleBrowserDialog)
  } else {
    window.removeEventListener('beforeunload', handleBrowserDialog)
  }
}

onBeforeUnmount(() => {
  handlePreventLeaving(false)
})

// Specs

const dataConsolidationType = ref<'average' | 'min' | 'max'>('max')
const specConsolidationType = makeSingleChoice('', [
  { name: 'average', title: props.i18n.average },
  { name: 'min', title: props.i18n.minimum },
  { name: 'max', title: props.i18n.maximum }
])
const backendValidationConsolidationType: ValidationMessages = []

const dataScalarType = ref<'warn' | 'crit' | 'min' | 'max'>('crit')
const specScalarType = makeSingleChoice('', [
  { name: 'warn', title: props.i18n.warning },
  { name: 'crit', title: props.i18n.critical },
  { name: 'min', title: props.i18n.minimum },
  { name: 'max', title: props.i18n.maximum }
])
const backendValidationScalarType: ValidationMessages = []

const dataConstant = ref(1)
const specConstant = makeFloat('', '')
const backendValidationConstant: ValidationMessages = []

const specLineType: SpecLineType = {
  line: props.i18n.line,
  area: props.i18n.area,
  stack: props.i18n.stack
}

const dataTransformation = ref(95)
const specTransformation = makeFloat('', props.i18n.percentile)
const backendValidationTransformation: ValidationMessages = []

const dataUnit = ref(convertToUnit(props.graph_options.unit))
const specUnit = makeCascadingSingleChoice('', [
  {
    name: 'first_entry_with_unit',
    title: props.i18n.unit_first_entry_with_unit,
    parameter_form: makeFixedValue(),
    default_value: null
  },
  {
    name: 'custom',
    title: props.i18n.unit_custom,
    parameter_form: makeDictionary('', [
      {
        name: 'notation',
        render_only: false,
        required: true,
        parameter_form: makeCascadingSingleChoice(props.i18n.unit_custom_notation, [
          {
            name: 'decimal',
            title: props.i18n.unit_custom_notation_decimal,
            parameter_form: makeString(props.i18n.unit_custom_notation_symbol, 'symbol', null),
            default_value: ''
          },
          {
            name: 'si',
            title: props.i18n.unit_custom_notation_si,
            parameter_form: makeString(props.i18n.unit_custom_notation_symbol, 'symbol', null),
            default_value: ''
          },
          {
            name: 'iec',
            title: props.i18n.unit_custom_notation_iec,
            parameter_form: makeString(props.i18n.unit_custom_notation_symbol, 'symbol', null),
            default_value: ''
          },
          {
            name: 'standard_scientific',
            title: props.i18n.unit_custom_notation_standard_scientific,
            parameter_form: makeString(props.i18n.unit_custom_notation_symbol, 'symbol', null),
            default_value: ''
          },
          {
            name: 'engineering_scientific',
            title: props.i18n.unit_custom_notation_engineering_scientific,
            parameter_form: makeString(props.i18n.unit_custom_notation_symbol, 'symbol', null),
            default_value: ''
          },
          {
            name: 'time',
            title: props.i18n.unit_custom_notation_time,
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
        parameter_form: makeDictionary(props.i18n.unit_custom_precision, [
          {
            name: 'type',
            render_only: false,
            required: true,
            parameter_form: makeSingleChoice(props.i18n.unit_custom_precision_type, [
              {
                name: 'auto',
                title: props.i18n.unit_custom_precision_type_auto
              },
              {
                name: 'strict',
                title: props.i18n.unit_custom_precision_type_strict
              }
            ]),
            default_value: 'auto',
            group: null
          },
          {
            name: 'digits',
            render_only: false,
            required: true,
            parameter_form: makeFloat(props.i18n.unit_custom_precision_digits, ''),
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
    title: props.i18n.explicit_vertical_range_auto,
    parameter_form: makeFixedValue(),
    default_value: null
  },
  {
    name: 'explicit',
    title: props.i18n.explicit_vertical_range_explicit,
    parameter_form: makeDictionary('', [
      {
        name: 'lower',
        render_only: false,
        required: true,
        parameter_form: makeFloat(props.i18n.explicit_vertical_range_explicit_lower, ''),
        default_value: 0.0,
        group: null
      },
      {
        name: 'upper',
        render_only: false,
        required: true,
        parameter_form: makeFloat(props.i18n.explicit_vertical_range_explicit_upper, ''),
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
    title: props.i18n.graph_lines,
    elements: [
      { ident: 'metric', title: props.i18n.metric },
      { ident: 'scalar', title: props.i18n.scalar },
      { ident: 'constant', title: props.i18n.constant }
    ]
  },
  {
    ident: 'graph_operations',
    title: props.i18n.graph_operations,
    elements: [
      { ident: 'operations', title: props.i18n.operations },
      { ident: 'transformation', title: props.i18n.transformation }
    ]
  },
  {
    ident: 'graph_options',
    title: props.i18n.graph_options,
    elements: [
      { ident: 'unit', title: props.i18n.unit },
      { ident: 'explicit_vertical_range', title: props.i18n.explicit_vertical_range },
      {
        ident: 'omit_zero_metrics',
        title: props.i18n.omit_zero_metrics
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
      return `${props.i18n.sum} ${props.i18n.of}`
    case 'product':
      return `${props.i18n.product} ${props.i18n.of}`
    case 'difference':
      return `${props.i18n.difference} ${props.i18n.of}`
    case 'fraction':
      return `${props.i18n.fraction} ${props.i18n.of}`
    case 'average':
      return `${props.i18n.average} ${props.i18n.of}`
    case 'minimum':
      return `${props.i18n.minimum} ${props.i18n.of}`
    case 'maximum':
      return `${props.i18n.maximum} ${props.i18n.of}`
    case 'transformation':
      return `${props.i18n.percentile} ${props.i18n.of}`
    default:
      return ''
  }
}

const dataMetric = ref<Metric>({
  hostName: null,
  serviceName: null,
  metricName: null
})
const dataScalar = ref<Metric>({
  hostName: null,
  serviceName: null,
  metricName: null
})

const graphLines: Ref<GraphLines> = ref(props.graph_lines)
const selectedGraphLines: Ref<GraphLines> = ref([])

function nextIndex(): number {
  if (graphLines.value.length === 0) {
    return 0
  } else {
    return Math.max(...graphLines.value.map((v) => v['id'])) + 1
  }
}

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
    id: nextIndex(),
    type: graphLine.type,
    color: graphLine.color,
    auto_title: graphLine.auto_title,
    custom_title: graphLine.custom_title,
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
        id: nextIndex(),
        type: graphLine.type,
        color: graphLine.color,
        auto_title: graphLine.auto_title,
        custom_title: graphLine.custom_title,
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
        id: nextIndex(),
        type: graphLine.type,
        color: graphLine.color,
        auto_title: graphLine.auto_title,
        custom_title: graphLine.custom_title,
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
        id: nextIndex(),
        type: graphLine.type,
        color: graphLine.color,
        auto_title: graphLine.auto_title,
        custom_title: graphLine.custom_title,
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
        id: nextIndex(),
        type: graphLine.type,
        color: graphLine.color,
        auto_title: graphLine.auto_title,
        custom_title: graphLine.custom_title,
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

function updateGraphLineAutoTitle(graphLine: GraphLine) {
  switch (graphLine.type) {
    case 'metric':
    case 'scalar': {
      const autoTitleParts = [graphLine.host_name, graphLine.service_name, graphLine.metric_name]
      graphLine.auto_title = `${autoTitleParts.filter((p) => p !== '').join(' > ')}`
      break
    }
    case 'constant':
      graphLine.auto_title = `${props.i18n.constant} ${graphLine.value}`
      break
    case 'transformation':
      graphLine.auto_title = `${props.i18n.percentile} ${graphLine.percentile} ${props.i18n.of} ${graphLine.operand.auto_title}`
  }
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

async function addMetric() {
  if (
    dataMetric.value.hostName !== '' &&
    dataMetric.value.hostName !== null &&
    dataMetric.value.serviceName !== '' &&
    dataMetric.value.serviceName !== null &&
    dataMetric.value.metricName !== '' &&
    dataMetric.value.metricName !== null
  ) {
    const color: string = await fetchMetricColor(
      dataMetric.value.metricName,
      dataConsolidationType.value
    )
    graphLines.value.push({
      id: nextIndex(),
      type: 'metric',
      color: color,
      auto_title: `${dataMetric.value.hostName} > ${dataMetric.value.serviceName} > ${dataMetric.value.metricName}`,
      custom_title: '',
      visible: true,
      line_type: 'line',
      mirrored: false,
      host_name: dataMetric.value.hostName,
      service_name: dataMetric.value.serviceName,
      metric_name: dataMetric.value.metricName,
      consolidation_type: dataConsolidationType.value
    })
    dataMetric.value = {
      hostName: null,
      serviceName: null,
      metricName: null
    }
  }
}

async function addScalar() {
  if (
    dataScalar.value.hostName !== '' &&
    dataScalar.value.hostName !== null &&
    dataScalar.value.serviceName !== '' &&
    dataScalar.value.serviceName !== null &&
    dataScalar.value.metricName !== '' &&
    dataScalar.value.metricName !== null
  ) {
    const color: string = await fetchMetricColor(dataScalar.value.metricName, dataScalarType.value)
    graphLines.value.push({
      id: nextIndex(),
      type: 'scalar',
      color: color,
      auto_title: `${dataScalar.value.hostName} > ${dataScalar.value.serviceName} > ${dataScalar.value.metricName}`,
      custom_title: '',
      visible: true,
      line_type: 'line',
      mirrored: false,
      host_name: dataScalar.value.hostName,
      service_name: dataScalar.value.serviceName,
      metric_name: dataScalar.value.metricName,
      scalar_type: dataScalarType.value
    })
    dataScalar.value = {
      hostName: null,
      serviceName: null,
      metricName: null
    }
  }
}

function addConstant() {
  graphLines.value.push({
    id: nextIndex(),
    type: 'constant',
    color: '#ff0000',
    auto_title: `${props.i18n.constant} ${dataConstant.value}`,
    custom_title: '',
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

function showSelectedIds(operator: '-' | '/') {
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
  const firstOperand = selectedGraphLines.value[0]
  if (firstOperand) {
    addGraphLineWithSelection({
      id: nextIndex(),
      type: 'sum',
      color: firstOperand.color,
      auto_title: `${props.i18n.sum} ${props.i18n.of} ${selectedGraphLines.value.map((l) => l.auto_title).join(', ')}`,
      custom_title: '',
      visible: true,
      line_type: 'line',
      mirrored: false,
      operands: selectedGraphLines.value
    })
  }
}

function applyProduct() {
  const firstOperand = selectedGraphLines.value[0]
  if (firstOperand) {
    addGraphLineWithSelection({
      id: nextIndex(),
      type: 'product',
      color: firstOperand.color,
      auto_title: `${props.i18n.product} ${props.i18n.of} ${selectedGraphLines.value.map((l) => l.auto_title).join(', ')}`,
      custom_title: '',
      visible: true,
      line_type: 'line',
      mirrored: false,
      operands: selectedGraphLines.value
    })
  }
}

function applyDifference() {
  const firstOperand = selectedGraphLines.value[0]
  if (firstOperand) {
    addGraphLineWithSelection({
      id: nextIndex(),
      type: 'difference',
      color: firstOperand.color,
      auto_title: `${props.i18n.difference} ${props.i18n.of} ${selectedGraphLines.value.map((l) => l.auto_title).join(', ')}`,
      custom_title: '',
      visible: true,
      line_type: 'line',
      mirrored: false,
      operands: selectedGraphLines.value
    })
  }
}

function applyFraction() {
  const firstOperand = selectedGraphLines.value[0]
  if (firstOperand) {
    addGraphLineWithSelection({
      id: nextIndex(),
      type: 'fraction',
      color: firstOperand.color,
      auto_title: `${props.i18n.fraction} ${props.i18n.of} ${selectedGraphLines.value.map((l) => l.auto_title).join(', ')}`,
      custom_title: '',
      visible: true,
      line_type: 'line',
      mirrored: false,
      operands: selectedGraphLines.value
    })
  }
}

function applyAverage() {
  const firstOperand = selectedGraphLines.value[0]
  if (firstOperand) {
    addGraphLineWithSelection({
      id: nextIndex(),
      type: 'average',
      color: firstOperand.color,
      auto_title: `${props.i18n.average} ${props.i18n.of} ${selectedGraphLines.value.map((l) => l.auto_title).join(', ')}`,
      custom_title: '',
      visible: true,
      line_type: 'line',
      mirrored: false,
      operands: selectedGraphLines.value
    })
  }
}

function applyMinimum() {
  const firstOperand = selectedGraphLines.value[0]
  if (firstOperand) {
    addGraphLineWithSelection({
      id: nextIndex(),
      type: 'minimum',
      color: firstOperand.color,
      auto_title: `${props.i18n.minimum} ${props.i18n.of} ${selectedGraphLines.value.map((l) => l.auto_title).join(', ')}`,
      custom_title: '',
      visible: true,
      line_type: 'line',
      mirrored: false,
      operands: selectedGraphLines.value
    })
  }
}

function applyMaximum() {
  const firstOperand = selectedGraphLines.value[0]
  if (firstOperand) {
    addGraphLineWithSelection({
      id: nextIndex(),
      type: 'maximum',
      color: firstOperand.color,
      auto_title: `${props.i18n.maximum} ${props.i18n.of} ${selectedGraphLines.value.map((l) => l.auto_title).join(', ')}`,
      custom_title: '',
      visible: true,
      line_type: 'line',
      mirrored: false,
      operands: selectedGraphLines.value
    })
  }
}

function applyTransformation() {
  const firstOperand = selectedGraphLines.value[0]
  if (firstOperand) {
    addGraphLineWithSelection({
      id: nextIndex(),
      type: 'transformation',
      color: firstOperand.color,
      auto_title: `${props.i18n.percentile} ${dataTransformation.value} ${props.i18n.of} ${firstOperand.auto_title}`,
      custom_title: '',
      visible: true,
      line_type: 'line',
      mirrored: false,
      percentile: dataTransformation.value,
      operand: firstOperand
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

// Graph update

function computeGraphOptions(): GraphOptions {
  return {
    unit: convertFromUnit(dataUnit.value),
    explicit_vertical_range: convertFromExplicitVerticalRange(dataExplicitVerticalRange.value),
    omit_zero_metrics: dataOmitZeroMetrics.value
  }
}

const graphContainerRef = ref()

onMounted(() => {
  props.graph_renderer(
    props.graph_id,
    graphLines.value,
    computeGraphOptions(),
    graphContainerRef.value
  )
})

watch(
  () => [
    graphLines.value,
    dataUnit.value,
    dataExplicitVerticalRange.value,
    dataOmitZeroMetrics.value
  ],
  () => {
    handlePreventLeaving(true)
    props.graph_renderer(
      props.graph_id,
      graphLines.value,
      computeGraphOptions(),
      graphContainerRef.value
    )
  },
  { deep: true }
)

// Form

window.addEventListener('submit', () => {
  handlePreventLeaving(false)
})

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
  <div ref="graphContainerRef"></div>

  <table ref="tableRef" class="data oddeven graph_designer_metrics">
    <tbody>
      <tr>
        <th class="header_narrow nowrap">#</th>
        <th class="header_buttons"></th>
        <th class="header_buttons">{{ props.i18n.actions }}</th>
        <th class="header_narrow">{{ props.i18n.color }}</th>
        <th class="header_nobr narrow">{{ props.i18n.auto_title }}</th>
        <th class="header_nobr narrow">{{ props.i18n.custom_title }}</th>
        <th class="header_buttons">{{ props.i18n.visible }}</th>
        <th class="header_narrow">{{ props.i18n.line_style }}</th>
        <th class="header_buttons">{{ props.i18n.mirrored }}</th>
        <th>{{ props.i18n.formula }}</th>
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
            :title="props.i18n.dissolve_operation"
            src="themes/facelift/images/icon_dissolve_operation.png"
            class="icon iconbutton png"
            @click="dissolveGraphLine(graphLine)"
          />
          <img
            :title="props.i18n.clone_this_entry"
            src="themes/facelift/images/icon_clone.svg"
            class="icon iconbutton"
            @click="cloneGraphLine(graphLine)"
          />
          <img
            :title="props.i18n.move_this_entry"
            src="themes/modern-dark/images/icon_drag.svg"
            class="icon iconbutton"
            @dragstart="dragStart"
            @drag="dragElement"
            @dragend="dragEnd"
          />
          <img
            :title="props.i18n.delete_this_entry"
            src="themes/facelift/images/icon_delete.svg"
            class="icon iconbutton"
            @click="deleteGraphLine(graphLine)"
          />
        </td>
        <td class="narrow"><CmkColorPicker v-model:data="graphLine.color" /></td>
        <td class="nobr narrow">{{ graphLine.auto_title }}</td>
        <td class="nobr narrow"><FormTitle v-model:data="graphLine.custom_title" /></td>
        <td class="buttons"><CmkSwitch v-model:data="graphLine.visible" /></td>
        <td class="narrow">
          <FormLineType v-model:data="graphLine.line_type" :spec="specLineType" />
        </td>
        <td class="buttons"><CmkSwitch v-model:data="graphLine.mirrored" /></td>
        <td>
          <div v-if="graphLine.type === 'metric'">
            <FixedMetricRowRenderer>
              <template #metric_cells>
                <FormMetricCells
                  v-model:host-name="graphLine.host_name"
                  v-model:service-name="graphLine.service_name"
                  v-model:metric-name="graphLine.metric_name"
                  :placeholder_host_name="props.i18n.placeholder_host_name"
                  :placeholder_service_name="props.i18n.placeholder_service_name"
                  :placeholder_metric_name="props.i18n.placeholder_metric_name"
                  @update:host-name="updateGraphLineAutoTitle(graphLine)"
                  @update:service-name="updateGraphLineAutoTitle(graphLine)"
                  @update:metric-name="updateGraphLineAutoTitle(graphLine)"
                />
              </template>
              <template #metric_type>
                <FormEdit
                  v-model:data="graphLine.consolidation_type"
                  :spec="specConsolidationType"
                  :backend-validation="backendValidationConsolidationType"
                />
              </template>
            </FixedMetricRowRenderer>
          </div>
          <div v-else-if="graphLine.type === 'scalar'">
            <FixedMetricRowRenderer>
              <template #metric_cells>
                <FormMetricCells
                  v-model:host-name="graphLine.host_name"
                  v-model:service-name="graphLine.service_name"
                  v-model:metric-name="graphLine.metric_name"
                  :placeholder_host_name="props.i18n.placeholder_host_name"
                  :placeholder_service_name="props.i18n.placeholder_service_name"
                  :placeholder_metric_name="props.i18n.placeholder_metric_name"
                  @update:host-name="updateGraphLineAutoTitle(graphLine)"
                  @update:service-name="updateGraphLineAutoTitle(graphLine)"
                  @update:metric-name="updateGraphLineAutoTitle(graphLine)"
                />
              </template>
              <template #metric_type>
                <FormEdit
                  v-model:data="graphLine.scalar_type"
                  :spec="specScalarType"
                  :backend-validation="backendValidationScalarType"
                />
              </template>
            </FixedMetricRowRenderer>
          </div>
          <div v-else-if="graphLine.type === 'constant'">
            {{ props.i18n.constant }}
            <FormEdit
              v-model:data="graphLine.value"
              :spec="specConstant"
              :backend-validation="backendValidationConstant"
              @update:data="updateGraphLineAutoTitle(graphLine)"
            />
          </div>
          <div v-else-if="graphLine.type === 'transformation'">
            <FormEdit
              v-model:data="graphLine.percentile"
              :spec="specTransformation"
              :backend-validation="backendValidationTransformation"
              @update:data="updateGraphLineAutoTitle(graphLine)"
            />
            {{ props.i18n.of }}
            <br />
            <div
              :style="{
                'background-color': graphLine.operand.color,
                'border-color': graphLine.operand.color
              }"
              class="color"
            ></div>
            {{ graphLine.operand.auto_title }}
          </div>
          <div v-else-if="isOperation(graphLine)">
            {{ formulaOf(graphLine) }}
            <div v-for="operand in graphLine.operands" :key="operand.id">
              <div
                :style="{ 'background-color': operand.color, 'border-color': operand.color }"
                class="color"
              ></div>
              {{ operand.auto_title }}
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
            <FormMetricCells
              v-model:host-name="dataMetric.hostName"
              v-model:service-name="dataMetric.serviceName"
              v-model:metric-name="dataMetric.metricName"
              :placeholder_host_name="props.i18n.placeholder_host_name"
              :placeholder_service_name="props.i18n.placeholder_service_name"
              :placeholder_metric_name="props.i18n.placeholder_metric_name"
            />
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
                :title="props.i18n.add"
                src="themes/facelift/images/icon_new.svg"
                class="icon iconbutton"
              />
              {{ props.i18n.add }}
            </button>
          </template>
        </MetricRowRenderer>
      </div>
    </template>
    <template #scalar>
      <div>
        <MetricRowRenderer>
          <template #metric_cells>
            <FormMetricCells
              v-model:host-name="dataScalar.hostName"
              v-model:service-name="dataScalar.serviceName"
              v-model:metric-name="dataScalar.metricName"
              :placeholder_host_name="props.i18n.placeholder_host_name"
              :placeholder_service_name="props.i18n.placeholder_service_name"
              :placeholder_metric_name="props.i18n.placeholder_metric_name"
            />
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
                :title="props.i18n.add"
                src="themes/facelift/images/icon_new.svg"
                class="icon iconbutton"
              />
              {{ props.i18n.add }}
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
            :title="props.i18n.add"
            src="themes/facelift/images/icon_new.svg"
            class="icon iconbutton"
          />
          {{ props.i18n.add }}
        </button>
      </div>
    </template>
    <template #operations>
      <div v-if="operationIsApplicable()">
        <button @click="applySum">{{ props.i18n.sum }}</button>
        <button @click="applyProduct">{{ props.i18n.product }}</button>
        <button @click="applyDifference">
          {{ props.i18n.difference }} {{ showSelectedIds('-') }}
        </button>
        <button @click="applyFraction">{{ props.i18n.fraction }} {{ showSelectedIds('/') }}</button>
        <button @click="applyAverage">{{ props.i18n.average }}</button>
        <button @click="applyMinimum">{{ props.i18n.minimum }}</button>
        <button @click="applyMaximum">{{ props.i18n.maximum }}</button>
      </div>
      <div v-else>{{ props.i18n.no_selected_graph_lines }}</div>
    </template>
    <template #transformation>
      <div v-if="transformationIsApplicable()">
        <FormEdit
          v-model:data="dataTransformation"
          :spec="specTransformation"
          :backend-validation="backendValidationTransformation"
        />
        <button @click="applyTransformation">{{ props.i18n.apply }}</button>
      </div>
      <div v-else>{{ props.i18n.no_selected_graph_line }}</div>
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
