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
import MapsSuggestionField from '@/maps/shared/components/MapsSuggestionField.vue'
import { namedSuggestions, suggestionList, titledSuggestions } from '@/maps/shared/suggestions'
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

const hosts = ref<string[]>([])
const services = ref<string[]>([])
const groups = ref<string[]>([])
const aggregationInfos = ref<AggregationInfo[]>([])
const loadingHosts = ref(false)
const loadingServices = ref(false)
const loadingGroups = ref(false)
const loadingAggregations = ref(false)
const hostModel = ref('')
const serviceModel = ref('')
const groupModel = ref('')
const aggregationModel = ref('')

const hostList = suggestionList(
  () => namedSuggestions(hosts.value),
  () => loadingHosts.value
)
const serviceList = suggestionList(
  () => namedSuggestions(services.value),
  () => loadingServices.value
)
const groupList = suggestionList(
  () => namedSuggestions(groups.value),
  () => loadingGroups.value
)
const aggregationList = suggestionList(
  () => titledSuggestions(aggregationInfos.value.map((a) => ({ id: a.id, title: a.title }))),
  () => loadingAggregations.value
)

async function loadHosts(): Promise<void> {
  loadingHosts.value = true
  hosts.value = await binding.hosts()
  loadingHosts.value = false
}

async function loadServices(host: string): Promise<void> {
  if (!host) {
    services.value = []
    return
  }
  loadingServices.value = true
  services.value = await binding.services(host)
  loadingServices.value = false
}

async function loadSourcesFor(kind: BindKind): Promise<void> {
  if (kind === 'host') {
    void loadHosts()
  } else if (kind === 'hostgroup' || kind === 'servicegroup') {
    loadingGroups.value = true
    groups.value = await (kind === 'hostgroup' ? binding.hostgroups() : binding.servicegroups())
    loadingGroups.value = false
  } else {
    loadingAggregations.value = true
    aggregationInfos.value = await binding.aggregations()
    loadingAggregations.value = false
  }
}

// Track the whole binding (not just the element id): a drag&drop bind or a
// type switch repatches the very element that is already selected, and the
// inputs must follow. Selecting in the autocomplete round-trips to the same
// value, so this never fights the user's typing.
watch(
  () => [
    props.element.id,
    bindKind.value,
    props.element.host_name,
    props.element.service_description,
    props.element.group_name,
    props.element.aggregation_id
  ],
  (next, prev) => {
    hostModel.value = props.element.host_name ?? ''
    serviceModel.value = props.element.service_description ?? ''
    groupModel.value = props.element.group_name ?? ''
    aggregationModel.value = props.element.aggregation_id ?? ''
    const idChanged = next[0] !== prev?.[0]
    const kindChanged = next[1] !== prev?.[1]
    if (idChanged || kindChanged) {
      void loadSourcesFor(bindKind.value)
    }
    if (bindKind.value === 'host') {
      if (!hostModel.value) {
        services.value = []
      } else if (idChanged || next[2] !== prev?.[2]) {
        void loadServices(hostModel.value)
      }
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
  hosts.value = []
  services.value = []
  groups.value = []
  aggregationInfos.value = []
  void loadSourcesFor(bindKind.value)
}

// The watch above re-syncs the models and reloads sources from the patched
// element — these handlers only commit the change.
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
        <MapsSuggestionField
          :label="_t('Host')"
          :model-value="hostModel"
          :list="hostList"
          :placeholder="_t('Bind to host…')"
          :empty-hint="_t('No hosts available')"
          @update:model-value="onHostChange"
        />
      </div>
      <div class="maps-presentation-binding-form__field">
        <span class="maps-cap">{{ _t('Service (optional)') }}</span>
        <MapsSuggestionField
          :label="_t('Service (optional)')"
          :model-value="serviceModel"
          :list="serviceList"
          :disabled="!hostModel"
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
      <MapsSuggestionField
        :label="bindKind === 'hostgroup' ? _t('Host group') : _t('Service group')"
        :model-value="groupModel"
        :list="groupList"
        :placeholder="_t('Pick a group…')"
        :empty-hint="_t('No groups available')"
        @update:model-value="onGroupChange"
      />
    </div>

    <div v-else class="maps-presentation-binding-form__field">
      <span class="maps-cap">{{ _t('BI aggregation') }}</span>
      <MapsSuggestionField
        :label="_t('BI aggregation')"
        :model-value="aggregationModel"
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
