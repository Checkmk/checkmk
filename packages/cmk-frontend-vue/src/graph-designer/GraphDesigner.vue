<!--
Copyright (C) 2024 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import {
  type GraphLine,
  type GraphLines,
  type GraphOptions,
  type Operation,
  type QueryAggregationHistogramPercentile,
  type QueryAggregationSumRate,
  type Transformation
} from 'cmk-shared-typing/typescript/graph_designer'
import { type Ref, computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import usei18n from '@/lib/i18n'
import useDragging from '@/lib/useDragging'

import CmkButton from '@/components/CmkButton.vue'
import CmkColorPicker from '@/components/CmkColorPicker.vue'
import CmkDropdown from '@/components/CmkDropdown.vue'
import CmkSwitch from '@/components/CmkSwitch.vue'
import type { Suggestion } from '@/components/suggestions'
import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'

import FixedMetricRowRenderer from '@/graph-designer/components/FixedMetricRowRenderer.vue'
import FormMetricCells, { type Metric } from '@/graph-designer/components/FormMetricCells.vue'
import FormQuery, { type Query } from '@/graph-designer/components/FormQuery.vue'
import FormTitle from '@/graph-designer/components/FormTitle.vue'
import GraphOptionsEditor from '@/graph-designer/components/GraphOptionsEditor.vue'
import MetricRowRenderer from '@/graph-designer/components/MetricRowRenderer.vue'
import TopicsRenderer from '@/graph-designer/components/TopicsRenderer.vue'
import {
  convertFromExplicitVerticalRange,
  convertFromUnit,
  convertToExplicitVerticalRange,
  convertToUnit
} from '@/graph-designer/converters'
import { fetchMetricColor, fetchMetricTypes } from '@/graph-designer/fetch_metric_properties'
import { type GraphRenderer } from '@/graph-designer/graph'

import type { Topic } from './type_defs'

const { _t } = usei18n()

const props = defineProps<{
  graph_id: string
  graph_lines: GraphLines
  graph_options: GraphOptions
  graph_renderer: GraphRenderer
  metric_backend_available: boolean
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
const consolidationTypeSuggestions: Suggestion[] = [
  { name: 'average', title: _t('Average') },
  { name: 'min', title: _t('Minimum') },
  { name: 'max', title: _t('Maximum') }
]

const dataScalarType = ref<'warn' | 'crit' | 'min' | 'max'>('crit')
const scalarTypeSuggestions: Suggestion[] = [
  { name: 'warn', title: _t('Warning') },
  { name: 'crit', title: _t('Critical') },
  { name: 'min', title: _t('Minimum') },
  { name: 'max', title: _t('Maximum') }
]

const dataConstant: Ref<number> = ref(1)

const formLineTypeSuggestions: Suggestion[] = [
  { name: 'line', title: _t('Line') },
  { name: 'area', title: _t('Area') },
  { name: 'stack', title: _t('Stack') }
]

const dataTransformation: Ref<number> = ref(95)

const dataUnit = ref(convertToUnit(props.graph_options.unit))

const dataExplicitVerticalRange = ref(
  convertToExplicitVerticalRange(props.graph_options.explicit_vertical_range)
)

const dataOmitZeroMetrics = ref(props.graph_options.omit_zero_metrics)

// Topics

const commonTopics: Topic[] = [
  {
    ident: 'graph_lines_standard',
    title: _t('Graph lines (Standard)'),
    elements: [
      { ident: 'metric', title: _t('Metric') },
      { ident: 'scalar', title: _t('Scalar') },
      { ident: 'constant', title: _t('Constant') },
      { ident: 'operations', title: _t('Operations') },
      { ident: 'transformation', title: _t('Transformation') }
    ]
  },
  {
    ident: 'graph_options',
    title: _t('Graph options'),
    elements: [],
    customContent: true
  }
]
let topics: Topic[]
if (props.metric_backend_available) {
  topics = [
    {
      ident: 'graph_lines_queries',
      title: _t('Graph lines (OpenTelemetry)'),
      elements: [{ ident: 'query', title: _t('Query') }]
    },
    ...commonTopics
  ]
} else {
  topics = commonTopics
}

// Graph lines

function formulaOf(graphLine: GraphLine): string {
  switch (graphLine.type) {
    case 'query':
    case 'metric':
    case 'scalar':
    case 'constant':
      return ''
    case 'sum':
      return `${_t('Sum')} ${_t('of')}`
    case 'product':
      return `${_t('Product')} ${_t('of')}`
    case 'difference':
      return `${_t('Difference')} ${_t('of')}`
    case 'fraction':
      return `${_t('Fraction')} ${_t('of')}`
    case 'average':
      return `${_t('Average')} ${_t('of')}`
    case 'minimum':
      return `${_t('Minimum')} ${_t('of')}`
    case 'maximum':
      return `${_t('Maximum')} ${_t('of')}`
    case 'transformation':
      return `${_t('Percentile')} ${_t('of')}`
    default:
      return ''
  }
}

const dataQuery = ref<Query>({
  metricName: null,
  resourceAttributes: [],
  scopeAttributes: [],
  dataPointAttributes: [],
  aggregationSum: null,
  aggregationHistogram: null
})
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

function changeSelection(graphLine: GraphLine, newValue: boolean) {
  if (newValue) {
    selectedGraphLines.value = [...selectedGraphLines.value, graphLine]
  } else {
    selectedGraphLines.value = selectedGraphLines.value.filter((g) => g.id !== graphLine.id)
  }
}

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
    case 'query':
      return {
        id: nextIndex(),
        type: graphLine.type,
        color: graphLine.color,
        auto_title: graphLine.auto_title,
        custom_title: graphLine.custom_title,
        visible: graphLine.visible,
        line_type: graphLine.line_type,
        mirrored: graphLine.mirrored,
        metric_name: graphLine.metric_name,
        resource_attributes: graphLine.resource_attributes,
        scope_attributes: graphLine.scope_attributes,
        data_point_attributes: graphLine.data_point_attributes,
        aggregation_sum: graphLine.aggregation_sum,
        aggregation_histogram: graphLine.aggregation_histogram
      }
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
    case 'query':
      graphLine.auto_title = `${_t('Query')} '${graphLine.metric_name}'`
      break
    case 'metric':
    case 'scalar': {
      const autoTitleParts = [graphLine.host_name, graphLine.service_name, graphLine.metric_name]
      graphLine.auto_title = `${autoTitleParts.filter((p) => p !== '').join(' > ')}`
      break
    }
    case 'constant':
      graphLine.auto_title = `${_t('Constant')} ${graphLine.value}`
      break
    case 'transformation':
      graphLine.auto_title = `${_t('Percentile')} ${graphLine.percentile} ${_t('of')} ${graphLine.operand.auto_title}`
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

async function addQuery() {
  if (dataQuery.value.metricName !== '' && dataQuery.value.metricName !== null) {
    const metricTypes: string[] = await fetchMetricTypes(
      dataQuery.value.metricName,
      dataQuery.value.resourceAttributes,
      dataQuery.value.scopeAttributes,
      dataQuery.value.dataPointAttributes
    )
    let aggregationSum: QueryAggregationSumRate | null
    if (metricTypes.includes('sum')) {
      aggregationSum = {
        type: 'rate',
        enabled: false,
        value: 1,
        unit: 'min'
      }
    } else {
      aggregationSum = null
    }
    let aggregationHistogram: QueryAggregationHistogramPercentile | null
    if (metricTypes.includes('histogram')) {
      aggregationHistogram = {
        type: 'percentile',
        enabled: false,
        value: 95
      }
    } else {
      aggregationHistogram = null
    }
    graphLines.value.push({
      id: nextIndex(),
      type: 'query',
      color: '#ff0000',
      auto_title: `${_t('Query')} '${dataQuery.value.metricName}'`,
      custom_title: '',
      visible: true,
      line_type: 'line',
      mirrored: false,
      metric_name: dataQuery.value.metricName,
      resource_attributes: dataQuery.value.resourceAttributes,
      scope_attributes: dataQuery.value.scopeAttributes,
      data_point_attributes: dataQuery.value.dataPointAttributes,
      aggregation_sum: aggregationSum,
      aggregation_histogram: aggregationHistogram
    })
    dataQuery.value = {
      metricName: null,
      resourceAttributes: [],
      scopeAttributes: [],
      dataPointAttributes: [],
      aggregationSum: null,
      aggregationHistogram: null
    }
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
    auto_title: `${_t('Constant')} ${dataConstant.value}`,
    custom_title: '',
    visible: true,
    line_type: 'line',
    mirrored: false,
    value: dataConstant.value
  })
  dataConstant.value = 1
}

// Operations on selected graph lines

function hasGraphQuery() {
  return selectedGraphLines.value.some((gl) => gl.type === 'query')
}

function operationIsApplicable() {
  return Object.keys(selectedGraphLines.value).length >= 2 && !hasGraphQuery()
}

function showSelectedIds(operator: '-' | '/') {
  return ` (${selectedGraphLines.value.map((l) => `#${l.id}`).join(` ${operator} `)})`
}

function transformationIsApplicable() {
  return Object.keys(selectedGraphLines.value).length === 1 && !hasGraphQuery()
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
      auto_title: `${_t('Sum')} ${_t('of')} ${selectedGraphLines.value.map((l) => l.auto_title).join(', ')}`,
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
      auto_title: `${_t('Product')} ${_t('of')} ${selectedGraphLines.value.map((l) => l.auto_title).join(', ')}`,
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
      auto_title: `${_t('Difference')} ${_t('of')} ${selectedGraphLines.value.map((l) => l.auto_title).join(', ')}`,
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
      auto_title: `${_t('Fraction')} ${_t('of')} ${selectedGraphLines.value.map((l) => l.auto_title).join(', ')}`,
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
      auto_title: `${_t('Average')} ${_t('of')} ${selectedGraphLines.value.map((l) => l.auto_title).join(', ')}`,
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
      auto_title: `${_t('Minimum')} ${_t('of')} ${selectedGraphLines.value.map((l) => l.auto_title).join(', ')}`,
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
      auto_title: `${_t('Maximum')} ${_t('of')} ${selectedGraphLines.value.map((l) => l.auto_title).join(', ')}`,
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
      auto_title: `${_t('Percentile')} ${dataTransformation.value} ${_t('of')} ${firstOperand.auto_title}`,
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
  return index % 2 === 0 ? 'even0' : 'odd0'
}

const { trContainerRef, dragStart, dragEnd, dragging } = useDragging()

function dragElement(event: DragEvent) {
  const dragReturn = dragging(event)
  if (dragReturn === null) {
    return
  }
  const movedEntry = graphLines.value.splice(dragReturn.draggedIndex, 1)[0]!
  graphLines.value.splice(dragReturn.targetIndex, 0, movedEntry)
}

// Create services

function createServices(graphLine: GraphLine) {
  if (graphLine.type !== 'query') {
    return
  }
}

// Graph update

function computeGraphOptions(): GraphOptions {
  return {
    unit: convertFromUnit(dataUnit.value),
    explicit_vertical_range: convertFromExplicitVerticalRange(dataExplicitVerticalRange.value),
    omit_zero_metrics: dataOmitZeroMetrics.value
  }
}

function updateGraphOptionsState(opts: GraphOptions) {
  dataUnit.value = convertToUnit(opts.unit)
  dataExplicitVerticalRange.value = convertToExplicitVerticalRange(opts.explicit_vertical_range)
  dataOmitZeroMetrics.value = opts.omit_zero_metrics
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
  <table class="data oddeven graph_designer_metrics">
    <thead>
      <tr>
        <th class="header_narrow nowrap">#</th>
        <th class="header_buttons"></th>
        <th class="header_buttons">{{ _t('Actions') }}</th>
        <th class="header_narrow">{{ _t('Color') }}</th>
        <th class="header_nobr narrow">{{ _t('Title') }}</th>
        <th class="header_nobr narrow">{{ _t('Custom title') }}</th>
        <th class="header_buttons">{{ _t('Visible') }}</th>
        <th class="header_narrow">{{ _t('Line style') }}</th>
        <th class="header_buttons">{{ _t('Mirrored') }}</th>
        <th>{{ _t('Formula') }}</th>
      </tr>
    </thead>
    <tbody ref="trContainerRef">
      <tr
        v-for="(graphLine, index) in graphLines"
        :key="graphLine.id"
        class="data"
        :class="computeOddEven(index)"
      >
        <td class="narrow nowrap">{{ graphLine.id }}</td>
        <td class="buttons">
          <div v-if="graphLine.type !== 'query'">
            <CmkCheckbox
              :model-value="selectedGraphLines.map((v) => v.id).includes(graphLine.id)"
              @update:model-value="(newValue) => changeSelection(graphLine, newValue)"
            />
          </div>
        </td>
        <td class="buttons">
          <img
            v-if="isDissolvable(graphLine)"
            :title="_t('Dissolve operation')"
            src="themes/facelift/images/icon_dissolve_operation.png"
            class="icon iconbutton png"
            @click="dissolveGraphLine(graphLine)"
          />
          <img
            :title="_t('Clone this entry')"
            src="themes/facelift/images/icon_clone.svg"
            class="icon iconbutton"
            @click="cloneGraphLine(graphLine)"
          />
          <img
            :title="_t('Move this entry')"
            src="themes/modern-dark/images/icon_drag.svg"
            class="icon iconbutton"
            @dragstart="dragStart"
            @drag="dragElement"
            @dragend="dragEnd"
          />
          <img
            :title="_t('Delete this entry')"
            src="themes/facelift/images/icon_delete.svg"
            class="icon iconbutton"
            @click="deleteGraphLine(graphLine)"
          />
          <img
            v-if="graphLine.type === 'query'"
            :title="_t('Create services')"
            src="themes/facelift/images/icon_checkmk.svg"
            class="icon iconbutton"
            @click="createServices(graphLine)"
          />
        </td>
        <td class="narrow"><CmkColorPicker v-model:data="graphLine.color" /></td>
        <td class="nobr narrow">{{ graphLine.auto_title }}</td>
        <td class="nobr narrow"><FormTitle v-model:data="graphLine.custom_title" /></td>
        <td class="buttons"><CmkSwitch v-model:data="graphLine.visible" /></td>

        <td class="narrow">
          <CmkDropdown
            v-model:selected-option="graphLine.line_type"
            :options="{
              type: 'fixed',
              suggestions: formLineTypeSuggestions
            }"
            :label="_t('Line style')"
          />
        </td>

        <td class="buttons"><CmkSwitch v-model:data="graphLine.mirrored" /></td>
        <td>
          <div v-if="graphLine.type === 'query'">
            {{ _t('Query') }}:
            <FormQuery
              v-model:metric-name="graphLine.metric_name"
              v-model:resource-attributes="graphLine.resource_attributes"
              v-model:scope-attributes="graphLine.scope_attributes"
              v-model:data-point-attributes="graphLine.data_point_attributes"
              v-model:aggregation-sum="graphLine.aggregation_sum"
              v-model:aggregation-histogram="graphLine.aggregation_histogram"
              @update:metric-name="updateGraphLineAutoTitle(graphLine)"
            />
          </div>
          <div v-else-if="graphLine.type === 'metric'">
            <FixedMetricRowRenderer>
              <template #metric_cells>
                <FormMetricCells
                  v-model:host-name="graphLine.host_name"
                  v-model:service-name="graphLine.service_name"
                  v-model:metric-name="graphLine.metric_name"
                  @update:host-name="updateGraphLineAutoTitle(graphLine)"
                  @update:service-name="updateGraphLineAutoTitle(graphLine)"
                  @update:metric-name="updateGraphLineAutoTitle(graphLine)"
                />
              </template>
              <template #metric_type>
                <CmkDropdown
                  v-model:selected-option="graphLine.consolidation_type"
                  :options="{
                    type: 'fixed',
                    suggestions: consolidationTypeSuggestions
                  }"
                  :label="_t('Formula')"
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
                  @update:host-name="updateGraphLineAutoTitle(graphLine)"
                  @update:service-name="updateGraphLineAutoTitle(graphLine)"
                  @update:metric-name="updateGraphLineAutoTitle(graphLine)"
                />
              </template>
              <template #metric_type>
                <CmkDropdown
                  v-model:selected-option="graphLine.scalar_type"
                  :options="{
                    type: 'fixed',
                    suggestions: scalarTypeSuggestions
                  }"
                  :label="_t('Scalar')"
                />
              </template>
            </FixedMetricRowRenderer>
          </div>
          <div v-else-if="graphLine.type === 'constant'">
            {{ _t('Constant') }}
            <CmkInput
              v-model="graphLine.value"
              type="number"
              @update:model-value="updateGraphLineAutoTitle(graphLine)"
            />
          </div>
          <div v-else-if="graphLine.type === 'transformation'">
            <CmkInput
              v-model="graphLine.percentile"
              type="number"
              @update:model-value="updateGraphLineAutoTitle(graphLine)"
            />
            {{ _t('of') }}
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
    <template #query>
      <div>
        <FormQuery
          v-model:metric-name="dataQuery.metricName"
          v-model:resource-attributes="dataQuery.resourceAttributes"
          v-model:scope-attributes="dataQuery.scopeAttributes"
          v-model:data-point-attributes="dataQuery.dataPointAttributes"
          v-model:aggregation-sum="dataQuery.aggregationSum"
          v-model:aggregation-histogram="dataQuery.aggregationHistogram"
        />
        <CmkButton @click="addQuery">
          {{ _t('Add') }}
        </CmkButton>
      </div>
    </template>
    <template #metric>
      <div>
        <MetricRowRenderer>
          <template #metric_cells>
            <FormMetricCells
              v-model:host-name="dataMetric.hostName"
              v-model:service-name="dataMetric.serviceName"
              v-model:metric-name="dataMetric.metricName"
            />
          </template>
          <template #metric_type>
            <CmkDropdown
              v-model:selected-option="dataConsolidationType"
              :options="{
                type: 'fixed',
                suggestions: consolidationTypeSuggestions
              }"
              :label="_t('Formula')"
            />
          </template>
          <template #metric_action>
            <CmkButton @click="addMetric">
              {{ _t('Add') }}
            </CmkButton>
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
            />
          </template>
          <template #metric_type>
            <CmkDropdown
              v-model:selected-option="dataScalarType"
              :options="{
                type: 'fixed',
                suggestions: scalarTypeSuggestions
              }"
              :label="_t('Scalar')"
            />
          </template>
          <template #metric_action>
            <CmkButton @click="addScalar">
              {{ _t('Add') }}
            </CmkButton>
          </template>
        </MetricRowRenderer>
      </div>
    </template>
    <template #constant>
      <div>
        <CmkInput v-model="dataConstant" type="number" />
        <CmkButton @click="addConstant">
          {{ _t('Add') }}
        </CmkButton>
      </div>
    </template>
    <template #operations>
      <div v-if="operationIsApplicable()">
        <CmkButton @click="applySum">
          {{ _t('Sum') }}
        </CmkButton>
        <CmkButton @click="applyProduct">
          {{ _t('Product') }}
        </CmkButton>
        <CmkButton @click="applyDifference">
          {{ _t('Difference') }} {{ showSelectedIds('-') }}
        </CmkButton>
        <CmkButton @click="applyFraction">
          {{ _t('Fraction') }} {{ showSelectedIds('-') }}
        </CmkButton>
        <CmkButton @click="applyAverage">
          {{ _t('Average') }}
        </CmkButton>
        <CmkButton @click="applyMinimum">
          {{ _t('Minimum') }}
        </CmkButton>
        <CmkButton @click="applyMaximum">
          {{ _t('Maximum') }}
        </CmkButton>
      </div>
      <div v-else>{{ _t('Select at least two graph lines to edit') }}</div>
    </template>
    <template #transformation>
      <div v-if="transformationIsApplicable()">
        {{ _t('Percentile') }}
        <CmkInput v-model="dataTransformation" type="number" />
        <CmkButton @click="applyTransformation">
          {{ _t('Apply') }}
        </CmkButton>
      </div>
      <div v-else>{{ _t('Select one graph line to edit') }}</div>
    </template>
    <template #graph_options_custom>
      <GraphOptionsEditor
        :graph_options="computeGraphOptions()"
        @update:graph-options="updateGraphOptionsState"
      />
    </template>
  </TopicsRenderer>

  <!-- This input field contains the computed json value which is sent when the form is submitted -->
  <input v-model="graphDesignerContentAsJson" name="graph_designer_content" type="hidden" />
</template>
