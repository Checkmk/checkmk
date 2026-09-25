<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkLoading from 'cmk-ui-library/components/CmkLoading.vue'
import CmkScrollContainer from 'cmk-ui-library/components/CmkScrollContainer.vue'
import CmkSearchInput from 'cmk-ui-library/components/CmkSearchInput.vue'
import CmkTabs, { CmkTab } from 'cmk-ui-library/components/CmkTabs'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { useDebounceRef } from 'cmk-ui-library/lib/useDebounce'
import { computed, onMounted, reactive, ref, watch } from 'vue'

import {
  type MonitoringObject,
  searchMonitoringObjects
} from '@/maps/shared/monitoringAutocompleters'
import type { ObjectState, PresentationElement } from '@/maps/types/api'
import { stateColor } from '@/maps/utils/stateColors'

import { isBindable } from '../binding'
import { BINDING_DROP_MIME, type BindingDropKind, type BindingDropPayload } from '../bindingDrop'
import { useDataBinding } from '../composables/useDataBinding'

const { _t } = usei18n()

const props = defineProps<{
  connectionId: string
  elements: PresentationElement[]
  states: Record<string, ObjectState>
}>()

const emit = defineEmits<{ close: [] }>()

const ROW_LIMIT = 200

const binding = useDataBinding(() => props.connectionId)

type Tab = 'hosts' | 'groups' | 'bi'
const tab = ref<Tab>('hosts')
function setTab(v: string | number): void {
  tab.value = String(v) as Tab
}

interface Row {
  kind: BindingDropKind
  name: string
  title: string
}

const rows = ref<Row[]>([])
const loading = ref(false)
const query = ref('')
const debouncedQuery = useDebounceRef(query)
const expanded = reactive(new Set<string>())
const loadingServices = reactive(new Set<string>())
const servicesByHost = reactive<Record<string, string[]>>({})

function asRows(kind: BindingDropKind, found: MonitoringObject[]): Row[] {
  return found.map((entry) => ({ kind, name: entry.name, title: entry.title }))
}

/**
 * Hosts and groups are searched on the server — a site's host list runs into
 * the thousands, and a list fetched once would only hold its first page. The BI
 * aggregations come as one list and are narrowed here.
 */
async function rowsFor(t: Tab, q: string): Promise<Row[]> {
  if (t === 'hosts') {
    return asRows('host', await searchMonitoringObjects('host', q))
  }
  if (t === 'groups') {
    const [hostgroups, servicegroups] = await Promise.all([
      searchMonitoringObjects('hostgroup', q),
      searchMonitoringObjects('servicegroup', q)
    ])
    return [...asRows('hostgroup', hostgroups), ...asRows('servicegroup', servicegroups)]
  }
  const needle = q.toLowerCase()
  return (await binding.aggregations())
    .map((a) => ({ kind: 'aggregation' as const, name: a.id, title: a.title || a.id }))
    .filter((row) => !needle || row.title.toLowerCase().includes(needle))
}

// Only the newest lookup may write: a slower answer for an earlier query or
// tab must not overwrite the list of the one now shown.
let loadSeq = 0
async function loadRows(): Promise<void> {
  const seq = ++loadSeq
  loading.value = true
  try {
    const found = await rowsFor(tab.value, debouncedQuery.value)
    if (seq === loadSeq) {
      rows.value = found
    }
  } finally {
    if (seq === loadSeq) {
      loading.value = false
    }
  }
}

onMounted(() => void loadRows())
// Another tab's rows must not stand in for this one's while it loads. A new
// query keeps the rows up until its answer replaces them, so typing does not
// make the list jump.
watch(tab, () => {
  rows.value = []
  void loadRows()
})
watch([debouncedQuery, () => props.connectionId], () => void loadRows())

const searchPlaceholder = computed(() =>
  tab.value === 'hosts'
    ? _t('Search hosts…')
    : tab.value === 'groups'
      ? _t('Search groups…')
      : _t('Search aggregations…')
)

const filteredRows = computed(() =>
  [...rows.value].sort((a, b) => a.title.localeCompare(b.title)).slice(0, ROW_LIMIT)
)
// Checkmk's autocompleters answer one entry past their limit when there are
// more, so only more rows than are shown means the list is cut.
const capped = computed(() => rows.value.length > ROW_LIMIT)

async function toggleHost(host: string): Promise<void> {
  if (expanded.has(host)) {
    expanded.delete(host)
    return
  }
  expanded.add(host)
  if (!servicesByHost[host] && !loadingServices.has(host)) {
    loadingServices.add(host)
    const found = await searchMonitoringObjects('service', '', host)
    servicesByHost[host] = found.map((entry) => entry.name)
    loadingServices.delete(host)
  }
}

// Live state is only known for objects already bound on the slide (states
// arrive keyed by element id) — show a worst-state dot for exactly those, and
// an "On slide" chip so the operator sees what's already wired up.
function bindingKey(kind: BindingDropKind, name: string, service?: string | null): string {
  return `${kind}|${name}|${service ?? ''}`
}

const boundStates = computed(() => {
  const map = new Map<string, string>()
  for (const el of props.elements) {
    if (!isBindable(el)) {
      continue
    }
    let key: string | null = null
    if (el.aggregation_id) {
      key = bindingKey('aggregation', el.aggregation_id)
    } else if (el.group_name && el.object_type === 'hostgroup') {
      key = bindingKey('hostgroup', el.group_name)
    } else if (el.group_name && el.object_type === 'servicegroup') {
      key = bindingKey('servicegroup', el.group_name)
    } else if (el.host_name) {
      key = bindingKey('host', el.host_name, el.service_description)
    }
    if (!key) {
      continue
    }
    const st = props.states[el.id]?.state
    if (st && !map.has(key)) {
      map.set(key, st)
    }
  }
  return map
})

function onSlide(p: { kind: BindingDropKind; name: string; service?: string | null }): boolean {
  return boundStates.value.has(bindingKey(p.kind, p.name, p.service))
}

function stateDotFor(p: {
  kind: BindingDropKind
  name: string
  service?: string | null
}): string | null {
  const st = boundStates.value.get(bindingKey(p.kind, p.name, p.service))
  return st ? stateColor(st) : null
}

function onDragStart(e: DragEvent, payload: BindingDropPayload): void {
  if (!e.dataTransfer) {
    return
  }
  e.dataTransfer.setData(BINDING_DROP_MIME, JSON.stringify(payload))
  e.dataTransfer.effectAllowed = 'copy'
}
</script>

<template>
  <aside class="maps-presentation-data-panel" @pointerdown.stop>
    <div class="maps-presentation-data-panel__head">
      <span class="maps-presentation-data-panel__title">{{ _t('Data browser') }}</span>
      <button class="maps-presentation-data-panel__x" :title="_t('Close')" @click="emit('close')">
        {{ untranslated('×') }}
      </button>
    </div>
    <CmkTabs
      :model-value="tab"
      class="maps-presentation-data-panel__tabs"
      @update:model-value="setTab"
    >
      <template #tabs>
        <CmkTab id="hosts">{{ _t('Hosts') }}</CmkTab>
        <CmkTab id="groups">{{ _t('Groups') }}</CmkTab>
        <CmkTab id="bi">{{ untranslated('BI') }}</CmkTab>
      </template>
    </CmkTabs>
    <CmkSearchInput
      v-model="query"
      :placeholder="searchPlaceholder"
      class="maps-presentation-data-panel__search"
    />
    <div class="maps-presentation-data-panel__hint">{{ _t('Drag an entry onto the slide') }}</div>
    <CmkScrollContainer class="maps-presentation-data-panel__list-wrap">
      <div class="maps-presentation-data-panel__list" :aria-busy="loading">
        <CmkLoading v-if="loading && !rows.length" />
        <div v-else-if="!filteredRows.length" class="maps-presentation-data-panel__empty">
          {{ query ? _t('Nothing matches your search') : _t('Nothing available') }}
        </div>

        <!-- Hosts with lazily expanded services -->
        <template v-if="tab === 'hosts'">
          <template v-for="row in filteredRows" :key="row.name">
            <div
              class="maps-presentation-data-panel__row maps-presentation-data-panel__row--host"
              draggable="true"
              @dragstart="onDragStart($event, { kind: 'host', name: row.name })"
            >
              <button
                class="maps-presentation-data-panel__chev"
                :class="{ 'maps-presentation-data-panel__chev--open': expanded.has(row.name) }"
                :title="expanded.has(row.name) ? _t('Collapse') : _t('Show services')"
                @click.stop="toggleHost(row.name)"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                  <path d="M9 6l6 6-6 6" />
                </svg>
              </button>
              <span
                v-if="stateDotFor({ kind: 'host', name: row.name })"
                class="maps-presentation-data-panel__dot"
                :style="{ background: stateDotFor({ kind: 'host', name: row.name }) ?? undefined }"
              />
              <span class="maps-presentation-data-panel__name" :title="row.name">{{
                row.name
              }}</span>
              <span
                v-if="onSlide({ kind: 'host', name: row.name })"
                class="maps-presentation-data-panel__chip"
              >
                {{ _t('On slide') }}
              </span>
            </div>
            <template v-if="expanded.has(row.name)">
              <CmkLoading v-if="loadingServices.has(row.name)" />
              <div
                v-for="svc in servicesByHost[row.name] ?? []"
                :key="`${row.name}|${svc}`"
                class="maps-presentation-data-panel__row maps-presentation-data-panel__row--svc"
                draggable="true"
                @dragstart="onDragStart($event, { kind: 'host', name: row.name, service: svc })"
              >
                <span
                  v-if="stateDotFor({ kind: 'host', name: row.name, service: svc })"
                  class="maps-presentation-data-panel__dot"
                  :style="{
                    background:
                      stateDotFor({ kind: 'host', name: row.name, service: svc }) ?? undefined
                  }"
                />
                <span class="maps-presentation-data-panel__name" :title="svc">{{ svc }}</span>
                <span
                  v-if="onSlide({ kind: 'host', name: row.name, service: svc })"
                  class="maps-presentation-data-panel__chip"
                >
                  {{ _t('On slide') }}
                </span>
              </div>
              <div
                v-if="
                  !loadingServices.has(row.name) && (servicesByHost[row.name] ?? []).length === 0
                "
                class="maps-presentation-data-panel__empty maps-presentation-data-panel__empty--svc"
              >
                {{ _t('No services') }}
              </div>
            </template>
          </template>
        </template>

        <!-- Host-/servicegroups and BI aggregations: flat draggable lists -->
        <template v-else>
          <div
            v-for="row in filteredRows"
            :key="`${row.kind}|${row.name}`"
            class="maps-presentation-data-panel__row maps-presentation-data-panel__row--host"
            draggable="true"
            @dragstart="onDragStart($event, { kind: row.kind, name: row.name })"
          >
            <span
              v-if="stateDotFor(row)"
              class="maps-presentation-data-panel__dot"
              :style="{ background: stateDotFor(row) ?? undefined }"
            />
            <span class="maps-presentation-data-panel__name" :title="row.title">{{
              row.title
            }}</span>
            <span v-if="onSlide(row)" class="maps-presentation-data-panel__chip">{{
              _t('On slide')
            }}</span>
          </div>
        </template>

        <div v-if="capped" class="maps-presentation-data-panel__more">
          {{ _t('Showing the first %{n} — keep typing to narrow results', { n: ROW_LIMIT }) }}
        </div>
      </div>
    </CmkScrollContainer>
  </aside>
</template>

<style scoped>
.maps-presentation-data-panel {
  display: flex;
  flex-direction: column;
  width: 260px;
  flex-shrink: 0;
  background: var(--ux-theme-3);
  border-right: 1px solid var(--default-border-color, rgb(255 255 255 / 8%));
  color: var(--font-color);
  z-index: 5;
}

.maps-presentation-data-panel__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-bottom: 1px solid var(--default-border-color, rgb(255 255 255 / 8%));
  min-height: 44px;
  box-sizing: border-box;
}

.maps-presentation-data-panel__title {
  font-weight: var(--font-weight-bold);
  font-size: var(--font-size-large);
}

.maps-presentation-data-panel__x {
  border: none;
  background: transparent;
  color: inherit;
  font-size: var(--font-size-xxlarge);
  cursor: pointer;
}

.maps-presentation-data-panel__tabs {
  padding: 8px 12px 0;
}

/* Vendored CmkTabs default to a boxy bar — slim it to an underline tab strip
   that fits the 260px panel, matching the sibling DetailDrawer. */
/* stylelint-disable-next-line selector-pseudo-class-no-unknown, checkmk/vue-bem-naming-convention */
.maps-presentation-data-panel__tabs :deep(.cmk-tabs__list) {
  gap: 0;
  border-bottom: 1px solid var(--default-border-color, rgb(255 255 255 / 8%));
}

/* stylelint-disable-next-line selector-pseudo-class-no-unknown, checkmk/vue-bem-naming-convention */
.maps-presentation-data-panel__tabs :deep(.cmk-tab__li) {
  padding: 5px 12px !important;
  font-size: var(--font-size-normal);
  line-height: 1;
  border-radius: 0;
  border-color: transparent;
  background: transparent;
  color: var(--font-color-dimmed);
}

/* stylelint-disable-next-line selector-pseudo-class-no-unknown, checkmk/vue-bem-naming-convention */
.maps-presentation-data-panel__tabs :deep(.cmk-tab__li[data-state='active']) {
  color: var(--font-color);
  background: transparent;
  border-bottom: 2px solid var(--color-corporate-green-50, rgb(34 197 94));
}

.maps-presentation-data-panel__search {
  margin: 10px 12px 0;
  width: calc(100% - 24px);
}

.maps-presentation-data-panel__hint {
  padding: 6px 12px 8px;
  font-size: var(--font-size-normal);
  color: var(--font-color-dimmed);
}

.maps-presentation-data-panel__list-wrap {
  flex: 1;
  min-height: 0;
}

.maps-presentation-data-panel__list {
  display: flex;
  flex-direction: column;
  padding-bottom: var(--dimension-4);
}

.maps-presentation-data-panel__row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  cursor: grab;
}

.maps-presentation-data-panel__row:hover {
  background: var(--input-hover-bg-color, rgb(255 255 255 / 6%));
}

.maps-presentation-data-panel__row--svc {
  padding-left: 34px;
  font-size: var(--font-size-normal);
  color: var(--font-color-dimmed);
}

.maps-presentation-data-panel__row--svc:hover {
  color: var(--font-color);
}

.maps-presentation-data-panel__chev {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  border: none;
  background: transparent;
  color: var(--font-color-dimmed);
  cursor: pointer;
  transition: transform 0.12s ease;
}

.maps-presentation-data-panel__chev svg {
  width: 10px;
  height: 10px;
}

.maps-presentation-data-panel__chev--open {
  transform: rotate(90deg);
}

.maps-presentation-data-panel__dot {
  width: 8px;
  height: 8px;
  flex-shrink: 0;
  border-radius: 9999px;
}

.maps-presentation-data-panel__name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.maps-presentation-data-panel__chip {
  flex-shrink: 0;
  padding: 1px 6px;
  border: 1px solid var(--color-corporate-green-50);
  border-radius: 9999px;
  font-size: var(--font-size-small);
  color: var(--color-corporate-green-50);
}

.maps-presentation-data-panel__empty {
  padding: 10px 12px;
  font-size: var(--font-size-normal);
  color: var(--font-color-dimmed);
}

.maps-presentation-data-panel__empty--svc {
  padding-left: 34px;
}

.maps-presentation-data-panel__more {
  padding: 8px 12px;
  font-size: var(--font-size-normal);
  font-style: italic;
  color: var(--font-color-dimmed);
  border-top: 1px solid var(--default-border-color, rgb(255 255 255 / 8%));
}
</style>
