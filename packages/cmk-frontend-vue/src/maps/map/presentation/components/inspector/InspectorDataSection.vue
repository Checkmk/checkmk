<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkCatalogPanel from 'cmk-ui-library/components/CmkCatalogPanel.vue'
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import CmkSwitch from 'cmk-ui-library/components/CmkSwitch.vue'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import useId from 'cmk-ui-library/lib/useId'
import { computed, ref, watch } from 'vue'

import ImagePicker from '@/maps/image-library/components/ImagePicker.vue'
import EditField from '@/maps/map/edit/components/EditField.vue'
import MapsSuggestionField from '@/maps/shared/components/MapsSuggestionField.vue'
import { suggestionList, titledSuggestions } from '@/maps/shared/suggestions'
import type {
  DataElement,
  ElementLabel,
  MetricChoice,
  PresentationTheme,
  ShapeElement
} from '@/maps/types/api'

import { useDataBinding } from '../../composables/useDataBinding'
import { connectorLabelVisible } from '../../connectorFlow'
import { fieldNumber } from '../../elements'
import { themeTokens } from '../../themes'
import ColorField from '../ColorField.vue'
import PresentationBindingForm from '../PresentationBindingForm.vue'
import PresentationGadgetMetricField from '../PresentationGadgetMetricField.vue'

const { _t } = usei18n()
const slotLabelId = useId()

const props = defineProps<{
  element: DataElement | ShapeElement
  connectionId: string
  targets: { id: string; name: string }[]
  theme: PresentationTheme
}>()

const emit = defineEmits<{ patch: [Record<string, unknown>] }>()

const tokens = computed(() => themeTokens(props.theme))

const connectorEl = computed<ShapeElement | null>(() =>
  props.element.kind === 'shape' &&
  (props.element.shape === 'line' || props.element.shape === 'arrow')
    ? props.element
    : null
)

const endpointOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: '', title: _t('Free') },
    ...props.targets
      .filter((t) => t.id !== props.element.id)
      .map((t) => ({ name: t.id, title: untranslated(t.name) }))
  ]
}))

const modeOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: 'icon', title: _t('Icon') },
    { name: 'text', title: _t('Text') },
    { name: 'gadget', title: _t('Gadget') }
  ]
}))

const gadgetOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: 'gauge', title: _t('Gauge') },
    { name: 'bar', title: _t('Bar') },
    { name: 'trafficlight', title: _t('Light') },
    { name: 'value', title: _t('Value') }
  ]
}))

function patchDisplay(p: Record<string, unknown>): void {
  if (props.element.kind !== 'data') {
    return
  }
  emit('patch', { display: { ...props.element.display, ...p } })
}

// A connector's value pill defaults to visible (label === null), a box
// shape's state label to hidden — the checkbox mirrors the effective state.
const effectiveLabelShow = computed(() =>
  connectorEl.value
    ? connectorLabelVisible(connectorEl.value)
    : (props.element.label?.show ?? false)
)

const labelBase = computed<ElementLabel>(() => {
  return (
    props.element.label ?? {
      show: true,
      text: null,
      size: 14,
      color: null,
      background: null,
      weight: 'bold',
      align: 'center'
    }
  )
})

function onLabelText(e: Event): void {
  const text = (e.target as HTMLInputElement).value
  emit('patch', { label: { ...labelBase.value, text: text || null } })
}

function patchLabelSize(value: unknown): void {
  const size = fieldNumber(value)
  if (size !== null) {
    emit('patch', { label: { ...labelBase.value, size } })
  }
}

// Data-element gadget metrics live in PresentationGadgetMetricField; only the
// connector flow/return pickers are sourced here.
const binding = useDataBinding(() => props.element.connection_id || props.connectionId)
const metrics = ref<MetricChoice[]>([])
const loadingMetrics = ref(false)
const flowMetricModel = ref('')

const metricList = suggestionList(
  () =>
    titledSuggestions(metrics.value.map((metric) => ({ id: metric.name, title: metric.title }))),
  () => loadingMetrics.value
)
const flowMetricBackModel = ref('')

// A metric picked for another object is almost always invalid, so a changed
// binding resets it. Connection and object-type switches null the host/service
// too, so this one watcher covers every binding change.
watch(
  () => [props.element.id, props.element.host_name, props.element.service_description] as const,
  async (curr, prev) => {
    const bindingChanged =
      prev !== undefined && prev[0] === curr[0] && (prev[1] !== curr[1] || prev[2] !== curr[2])

    if (bindingChanged) {
      if (connectorEl.value?.flow_metric || connectorEl.value?.flow_metric_back) {
        emit('patch', { flow_metric: null, flow_metric_back: null })
      }
      flowMetricModel.value = ''
      flowMetricBackModel.value = ''
    } else {
      flowMetricModel.value = (connectorEl.value?.flow_metric ?? '') as string
      flowMetricBackModel.value = (connectorEl.value?.flow_metric_back ?? '') as string
    }

    // Only connectors consume this list (flow/return pickers) — a data element's
    // gadget metric is sourced by PresentationGadgetMetricField, so don't fetch.
    const host = props.element.host_name
    if (!host || !connectorEl.value) {
      metrics.value = []
      return
    }
    loadingMetrics.value = true
    metrics.value = await binding.metrics(host, props.element.service_description)
    loadingMetrics.value = false
  },
  { immediate: true }
)
</script>

<template>
  <CmkCatalogPanel :title="_t('Data')">
    <div class="maps-inspector-data-section">
      <PresentationBindingForm
        :element="element"
        :connection-id="connectionId"
        @patch="emit('patch', $event)"
      />
      <!-- No <label> around the switch: its slider toggles itself, and a label
           would pass the click on to the hidden checkbox, switching it back. -->
      <span v-if="element.kind === 'shape'" class="maps-inspector-data-section__slot">
        <CmkSwitch
          :model-value="element.data_slot ?? false"
          :aria-labelledby="slotLabelId"
          @update:model-value="emit('patch', { data_slot: $event })"
        />
        <span
          :id="slotLabelId"
          class="maps-inspector-data-section__slot-label"
          @click="emit('patch', { data_slot: !element.data_slot })"
        >
          {{ _t('Data slot (fill in connect mode)') }}
        </span>
      </span>
    </div>
  </CmkCatalogPanel>

  <CmkCatalogPanel :title="_t('Display')">
    <div class="maps-inspector-data-section">
      <template v-if="element.kind === 'data'">
        <EditField class="maps-inspector-data-section__field" :label="_t('Show as')">
          <CmkDropdown
            :model-value="element.display.mode"
            :options="modeOptions"
            :width="'fill'"
            :label="_t('Show as')"
            @update:model-value="patchDisplay({ mode: $event })"
          />
        </EditField>
        <EditField
          v-if="element.display.mode === 'icon'"
          class="maps-inspector-data-section__field"
          :label="_t('Icon')"
        >
          <ImagePicker
            :model-value="element.display.image ?? ''"
            :placeholder="_t('State dot (default)')"
            @update:model-value="patchDisplay({ image: $event || null })"
          />
        </EditField>
        <template v-if="element.display.mode === 'gadget'">
          <EditField class="maps-inspector-data-section__field" :label="_t('Gadget')">
            <CmkDropdown
              :model-value="element.display.gadget_type ?? 'gauge'"
              :options="gadgetOptions"
              :width="'fill'"
              :label="_t('Gadget')"
              @update:model-value="patchDisplay({ gadget_type: $event })"
            />
          </EditField>
        </template>
        <!-- Outside the gadget block on purpose: the field self-hides off-gadget,
             but its mount keeps the binding-change metric reset running in every
             display mode. -->
        <PresentationGadgetMetricField
          :element="element"
          :connection-id="connectionId"
          @patch="emit('patch', $event)"
        />
        <EditField class="maps-inspector-data-section__field" :label="_t('Fill')">
          <ColorField
            :label="_t('Fill')"
            :value="element.fill"
            :default-color="tokens['--pres-shape-fill']"
            @set="emit('patch', { fill: $event })"
          />
        </EditField>
      </template>

      <CmkCheckbox
        :model-value="effectiveLabelShow"
        :label="_t('Show label')"
        @update:model-value="emit('patch', { label: { ...labelBase, show: $event } })"
      />
      <template v-if="effectiveLabelShow">
        <EditField class="maps-inspector-data-section__field" :label="_t('Label text')">
          <CmkInput
            field-size="fill"
            :model-value="element.label?.text ?? ''"
            :aria-label="_t('Label text')"
            :placeholder="element.service_description || element.host_name || _t('Automatic')"
            @change="onLabelText"
          />
        </EditField>
        <div class="maps-inspector-data-section__row">
          <EditField
            v-slot="{ id }"
            class="maps-inspector-data-section__num"
            labels-control
            :label="_t('Label size')"
          >
            <CmkInput
              :id="id"
              type="number"
              unit="px"
              :model-value="element.label?.size ?? 14"
              min="6"
              max="96"
              @update:model-value="patchLabelSize($event)"
            />
          </EditField>
          <EditField class="maps-inspector-data-section__field" :label="_t('Label color')">
            <ColorField
              :label="_t('Label color')"
              :value="element.label?.color"
              :default-color="tokens['--pres-fg']"
              @set="emit('patch', { label: { ...labelBase, color: $event } })"
            />
          </EditField>
        </div>
      </template>
    </div>
  </CmkCatalogPanel>

  <CmkCatalogPanel v-if="connectorEl" :title="_t('Connector')">
    <div class="maps-inspector-data-section">
      <EditField class="maps-inspector-data-section__field" :label="_t('Start endpoint')">
        <CmkDropdown
          :model-value="connectorEl.start_ref ?? ''"
          :options="endpointOptions"
          :width="'fill'"
          :label="_t('Start endpoint')"
          @update:model-value="emit('patch', { start_ref: $event || null })"
        />
      </EditField>
      <EditField class="maps-inspector-data-section__field" :label="_t('End endpoint')">
        <CmkDropdown
          :model-value="connectorEl.end_ref ?? ''"
          :options="endpointOptions"
          :width="'fill'"
          :label="_t('End endpoint')"
          @update:model-value="emit('patch', { end_ref: $event || null })"
        />
      </EditField>
      <CmkCheckbox
        :model-value="connectorEl.flow ?? false"
        :label="_t('Animate flow (weathermap)')"
        @update:model-value="emit('patch', { flow: $event })"
      />
      <template v-if="connectorEl.flow">
        <EditField class="maps-inspector-data-section__field" :label="_t('Flow metric')">
          <MapsSuggestionField
            :label="_t('Flow metric')"
            :model-value="flowMetricModel"
            :list="metricList"
            :placeholder="element.host_name ? _t('Pick a metric…') : _t('e.g. if_in_bps')"
            @update:model-value="emit('patch', { flow_metric: $event || null })"
          />
        </EditField>
        <EditField
          class="maps-inspector-data-section__field"
          :label="_t('Return metric (optional)')"
        >
          <MapsSuggestionField
            :label="_t('Return metric (optional)')"
            :model-value="flowMetricBackModel"
            :list="metricList"
            :placeholder="_t('Splits the link into a two-way weathermap')"
            @update:model-value="emit('patch', { flow_metric_back: $event || null })"
          />
        </EditField>
      </template>
    </div>
  </CmkCatalogPanel>
</template>

<style scoped>
.maps-inspector-data-section {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-5);
  padding: var(--dimension-4) 0;
}

.maps-inspector-data-section__row {
  display: flex;
  align-items: flex-start;
  gap: var(--dimension-4);
}

.maps-inspector-data-section__field,
.maps-inspector-data-section__num {
  min-width: 0;
  flex: 1;
}

.maps-inspector-data-section__note {
  font-size: var(--font-size-normal);
  color: var(--font-color-dimmed);
}

.maps-inspector-data-section__slot {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
}

.maps-inspector-data-section__slot-label {
  font-size: var(--font-size-normal);
  color: var(--font-color);
  cursor: pointer;
}
</style>
