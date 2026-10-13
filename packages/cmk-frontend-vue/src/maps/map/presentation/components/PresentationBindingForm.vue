<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed, onMounted, ref, watch } from 'vue'

import { useConnections } from '@/maps/services/context'
import MapsObjectField from '@/maps/shared/components/MapsObjectField.vue'
import MapsSuggestionField from '@/maps/shared/components/MapsSuggestionField.vue'
import { suggestionList, titledSuggestions } from '@/maps/shared/suggestions'
import type { AggregationInfo, DataElement, ShapeElement } from '@/maps/types/api'

import { EMPTY_BINDING } from '../binding'
import { useDataBinding } from '../composables/useDataBinding'

const { _t } = usei18n()

const props = defineProps<{
  element: DataElement | ShapeElement
  // The map's default connection — used when the element carries none.
  connectionId: string
}>()

const emit = defineEmits<{ patch: [Record<string, unknown>] }>()

// Sentinel for "inherit the map's connection" (stored as null).
const DEFAULT_CONNECTION = ''

const connectionsStore = useConnections()
const connectionOptions = ref<{
  type: 'fixed'
  suggestions: { name: string; title: TranslatedString }[]
}>({
  type: 'fixed',
  suggestions: []
})

function effectiveConnection(): string {
  return props.element.connection_id || props.connectionId
}

const binding = useDataBinding(effectiveConnection)

// "host" covers the host + optional service pair; groups and BI aggregations
// carry an explicit object_type so the state service resolves them per type.
// Mirrors the backend derivation in state_service._object_type — change both
// together.
type BindKind = 'host' | 'hostgroup' | 'servicegroup' | 'aggregation'

const bindKind = computed<BindKind>(() => {
  const t = props.element.object_type
  if (t === 'hostgroup' || t === 'servicegroup' || t === 'aggregation') {
    return t
  }
  if (props.element.aggregation_id) {
    return 'aggregation'
  }
  return 'host'
})

const bindKindOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: 'host', title: _t('Host / service') },
    { name: 'hostgroup', title: _t('Host group') },
    { name: 'servicegroup', title: _t('Service group') },
    { name: 'aggregation', title: _t('BI aggregation') }
  ]
}))

function onBindKindChange(v: string | null): void {
  const kind = (v ?? 'host') as BindKind
  if (kind === bindKind.value) {
    return
  }
  // Switching the type clears the whole binding — stale fields from another
  // type must not linger in the element.
  emit('patch', { ...EMPTY_BINDING, object_type: kind === 'host' ? null : kind })
}

const aggregationInfos = ref<AggregationInfo[]>([])
const loadingAggregations = ref(false)

const aggregationList = suggestionList(
  () => titledSuggestions(aggregationInfos.value.map((a) => ({ id: a.id, title: a.title }))),
  () => loadingAggregations.value
)

// Hosts, services and groups are searched as the operator types; only the BI
// aggregations come as one list.
async function loadAggregations(): Promise<void> {
  loadingAggregations.value = true
  aggregationInfos.value = await binding.aggregations()
  loadingAggregations.value = false
}

watch(
  [() => props.element.id, bindKind],
  () => {
    if (bindKind.value === 'aggregation') {
      void loadAggregations()
    }
  },
  { immediate: true }
)

onMounted(async () => {
  if (connectionsStore.connections.value.length === 0) {
    await connectionsStore.fetch()
  }
  connectionOptions.value = {
    type: 'fixed',
    suggestions: [
      { name: DEFAULT_CONNECTION, title: _t('Map default') },
      ...connectionsStore.connections.value.map((c) => ({
        name: c.id,
        title: untranslated(c.label || c.id)
      }))
    ]
  }
})

function onConnectionChange(v: string | null): void {
  emit('patch', {
    ...EMPTY_BINDING,
    object_type: props.element.object_type ?? null,
    connection_id: v || null
  })
  aggregationInfos.value = []
  if (bindKind.value === 'aggregation') {
    void loadAggregations()
  }
}

function onHostChange(v: string): void {
  emit('patch', { host_name: v || null, service_description: null })
}

function onServiceChange(v: string): void {
  emit('patch', { service_description: v || null })
}

function onGroupChange(v: string): void {
  emit('patch', { group_name: v || null })
}

function onAggregationChange(v: string): void {
  // Carry the human-readable title onto the element name — labels and the
  // layers panel would otherwise show the raw aggregation id.
  const title = aggregationInfos.value.find((a) => a.id === v)?.title
  emit('patch', { aggregation_id: v || null, ...(title ? { name: title } : {}) })
}
</script>

<template>
  <div class="maps-presentation-binding-form">
    <div
      v-if="connectionOptions.suggestions.length > 1"
      class="maps-presentation-binding-form__field"
    >
      <span class="maps-cap">{{ _t('Connection') }}</span>
      <CmkDropdown
        :model-value="element.connection_id ?? DEFAULT_CONNECTION"
        :options="connectionOptions"
        :width="'fill'"
        :label="_t('Connection')"
        @update:model-value="onConnectionChange"
      />
    </div>

    <div class="maps-presentation-binding-form__field">
      <span class="maps-cap">{{ _t('Object type') }}</span>
      <CmkDropdown
        :model-value="bindKind"
        :options="bindKindOptions"
        :width="'fill'"
        :label="_t('Object type')"
        @update:model-value="onBindKindChange"
      />
    </div>

    <template v-if="bindKind === 'host'">
      <div class="maps-presentation-binding-form__field">
        <span class="maps-cap">{{ _t('Host') }}</span>
        <MapsObjectField
          kind="host"
          :label="_t('Host')"
          :model-value="element.host_name ?? ''"
          :placeholder="_t('Bind to host…')"
          @update:model-value="onHostChange"
        />
      </div>
      <div class="maps-presentation-binding-form__field">
        <span class="maps-cap">{{ _t('Service (optional)') }}</span>
        <MapsObjectField
          kind="service"
          :host-name="element.host_name ?? ''"
          :label="_t('Service (optional)')"
          :model-value="element.service_description ?? ''"
          :placeholder="_t('Whole host if empty')"
          @update:model-value="onServiceChange"
        />
      </div>
    </template>

    <div
      v-else-if="bindKind === 'hostgroup' || bindKind === 'servicegroup'"
      class="maps-presentation-binding-form__field"
    >
      <span class="maps-cap">{{
        bindKind === 'hostgroup' ? _t('Host group') : _t('Service group')
      }}</span>
      <MapsObjectField
        :kind="bindKind"
        :label="bindKind === 'hostgroup' ? _t('Host group') : _t('Service group')"
        :model-value="element.group_name ?? ''"
        :placeholder="_t('Pick a group…')"
        @update:model-value="onGroupChange"
      />
    </div>

    <div v-else class="maps-presentation-binding-form__field">
      <span class="maps-cap">{{ _t('BI aggregation') }}</span>
      <MapsSuggestionField
        :label="_t('BI aggregation')"
        :model-value="element.aggregation_id ?? ''"
        :list="aggregationList"
        :placeholder="_t('Pick an aggregation…')"
        :empty-hint="_t('No aggregations available')"
        @update:model-value="onAggregationChange"
      />
    </div>

    <!-- A gadget's metric belongs with the service it reads — host/service
         consumers drop the picker in here, right under the binding. -->
    <slot name="after-binding" />

    <CmkCheckbox
      v-if="bindKind === 'host' || bindKind === 'aggregation'"
      :model-value="element.only_hard_states ?? false"
      :label="_t('Only hard states')"
      @update:model-value="emit('patch', { only_hard_states: $event })"
    />
  </div>
</template>

<style scoped>
.maps-presentation-binding-form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
}

.maps-presentation-binding-form__field {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}
</style>
