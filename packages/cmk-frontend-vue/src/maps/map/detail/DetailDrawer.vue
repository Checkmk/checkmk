<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Everything monitoring knows about one object, next to the map it sits on.

The map answers "what is wrong"; this answers "what exactly, and what do I do
about it". It slides in over the map rather than replacing it, because the
answer often is another object on the same map -- so it is a side panel of the
map, not a dialog: the map stays readable and clickable while it is open.

This is the shell: it holds what the object *is* -- the streamed state, the
details fetched on demand, the group members, the metric semantics -- and hands
each tab what that tab shows. Which facts are worth stating, and how, belongs
to the tabs. A tab only appears when it has something in it.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkTabs, { CmkTab, CmkTabContent } from 'cmk-ui-library/components/CmkTabs'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, nextTick, ref, useTemplateRef, watch } from 'vue'

import type { CommandVerb } from '@/maps/api/ticket'
import { useMetricInfo } from '@/maps/map/composables/useMetricInfo'
import { metricTitlesOf, metricUnitsOf } from '@/maps/map/composables/useMetricUnits'
import { useAuth } from '@/maps/services/context'
import type { BulkAckTarget, MapElement, ObjectState } from '@/maps/types/api'
import { objectTypeLabel } from '@/maps/utils/dropdownOptions'
import { buildCheckmkUrl, stripCheckmkBase, summarySubject } from '@/maps/utils/mapNavigation'
import { getEffectiveObjectType, getMapElementName } from '@/maps/utils/naming'
import { stateColorVar } from '@/maps/utils/stateColors'

import { activityCount } from './activityFacts'
import DetailActions from './components/DetailActions.vue'
import DetailActivityTab from './components/DetailActivityTab.vue'
import DetailAggregationSection from './components/DetailAggregationSection.vue'
import DetailContextTab from './components/DetailContextTab.vue'
import DetailHeader from './components/DetailHeader.vue'
import DetailMembersTab from './components/DetailMembersTab.vue'
import DetailPerformanceTab from './components/DetailPerformanceTab.vue'
import DetailStatusTab from './components/DetailStatusTab.vue'
import { useAggregationDetail } from './composables/useAggregationDetail'
import { useGroupMembers } from './composables/useGroupMembers'
import { useNowTicker } from './composables/useNowTicker'
import { useObjectDetailsFetch } from './composables/useObjectDetailsFetch'
import { usePerformanceHistory } from './composables/usePerformanceHistory'
import { usePerformanceMetrics } from './composables/usePerformanceMetrics'
import { useSummaryChips } from './composables/useSummaryChips'
import { hasContextFacts } from './contextFacts'
import { isProblemState, severityKindOf, sinceText } from './statusFacts'

const props = defineProps<{
  object: MapElement | null
  state?: ObjectState | undefined
  checkmkUrl?: string | null
  /** The map's connection, for the details this drawer fetches itself. */
  connectionId?: string | null
  /**
   * Host names on this map. A topology entry naming one of them can be
   * followed on the map; the others are only names.
   */
  selectableHosts?: string[]
  /**
   * Whether this drawer is on a surface nobody is operating -- a kiosk wall, the
   * settings live preview. Not whether the map's definition can be edited: a
   * built-in map is read-only to the editor and still a place to acknowledge a
   * problem from.
   */
  unattended?: boolean
}>()

const emit = defineEmits<{
  close: []
  acknowledge: []
  'remove-ack': []
  'schedule-downtime': []
  'remove-downtime': []
  'force-check': []
  'add-comment': []
  'enable-notifications': []
  'disable-notifications': []
  /**
   * A host was picked out of the drawer -- from the topology, a group's members
   * or an aggregation's leaves. ``seed`` carries a state for targets that never
   * enter the map's own state stream, so the drawer they open is not blank.
   */
  'select-host': [
    hostName: string,
    serviceDescription?: string | null,
    seed?: Omit<ObjectState, 'object_id'> | null
  ]
  /** Acknowledge the real hosts/services contributing to an aggregation. */
  'bulk-acknowledge': [targets: BulkAckTarget[]]
}>()

const { _t } = usei18n()
const auth = useAuth()

const nowMs = useNowTicker()

const canCommand = (verb: CommandVerb): boolean => !props.unattended && auth.mayCommand(verb)

// Long output, comments, downtimes and topology are large and rarely change, so
// they are fetched for the open object rather than streamed with its state.
const { details } = useObjectDetailsFetch({
  object: () => props.object,
  connectionId: () => props.connectionId
})

// Checkmk's own display semantics for this check -- its Perf-O-Meter, its
// registered units and titles -- so the performance tab reads the way the
// Checkmk GUI does rather than inventing its own formatting.
const { info: metricInfo } = useMetricInfo({
  connectionId: () => props.object?.connection_id ?? props.connectionId,
  hostName: () => props.object?.host_name,
  serviceDescription: () => props.object?.service_description,
  perfData: () => props.state?.perf_data,
  checkCommand: () => props.state?.check_command,
  enabled: () => !!props.object?.host_name && !!props.object?.service_description
})
const perfometer = computed(() => metricInfo.value?.perfometer ?? null)

const {
  groupMembers,
  loadingMembers,
  memberSearch,
  onlyProblems,
  filteredMembers,
  visibleMembers,
  truncatedMemberCount,
  memberChips,
  memberStateTone,
  memberStateBadge,
  isGroup
} = useGroupMembers({
  object: () => props.object,
  connectionId: () => props.connectionId
})

const {
  perfRows,
  mainMetric,
  mainPerfRow,
  otherPerfRows,
  mainHeadline,
  longOutputRows,
  longOutputText
} = usePerformanceMetrics({
  state: () => props.state,
  details,
  perfometer,
  metricUnits: computed(() => metricUnitsOf(metricInfo.value)),
  metricTitles: computed(() => metricTitlesOf(metricInfo.value))
})

const showPerformanceTab = computed(() => perfRows.value.length > 0 || !!longOutputText.value)

const { historyData, mainHistoryKey, mainThresholds, HISTORY_MINUTES } = usePerformanceHistory({
  object: () => props.object,
  connectionId: () => props.connectionId,
  mainMetric,
  showPerformanceTab: () => showPerformanceTab.value
})

const isSite = computed(() => props.object?.type === 'site')
const isAggregation = computed(() => props.object?.type === 'aggregation')

// A dyngroup's scope is its bundled hosts where it names them, and otherwise
// whatever its filter actually matched -- which is what its members are.
const dyngroupHosts = computed<string[] | null>(() => {
  if (props.object?.type !== 'dyngroup') {
    return null
  }
  if (props.object.bundle_hosts?.length) {
    return props.object.bundle_hosts
  }
  const hosts = [...new Set(groupMembers.value.map((member) => member.host).filter(Boolean))]
  return hosts.length ? hosts : null
})

const { serviceChips, hostChips } = useSummaryChips({
  object: () => props.object,
  state: () => props.state,
  checkmkUrl: () => props.checkmkUrl,
  isSite: () => isSite.value,
  dyngroupHosts: () => dyngroupHosts.value
})

const serviceChipsLabel = computed(() =>
  props.object && summarySubject(props.object) === 'hosts' ? _t('Hosts') : _t('Services')
)

const {
  checkmkSetupUrlFull,
  aggregationSummary,
  aggregationView,
  aggregationViewOptions,
  setAggregationView,
  aggregationListRows,
  aggregationListMultiHost,
  activeChips,
  onAggregationLeafClick,
  aggregationProblemLeaves,
  onBulkAcknowledgeClick
} = useAggregationDetail({
  object: () => props.object,
  state: () => props.state,
  checkmkUrl: () => props.checkmkUrl,
  connectionId: () => props.connectionId,
  onSelectHost: (host, service, seed) => emit('select-host', host, service, seed),
  onBulkAcknowledge: (targets) => emit('bulk-acknowledge', targets)
})

const displayName = computed(() => (props.object ? (getMapElementName(props.object) ?? '') : ''))
const typeLabel = computed(() =>
  props.object ? objectTypeLabel(getEffectiveObjectType(props.object), _t) : ''
)
const severityKind = computed(() => severityKindOf(props.state))

const checkmkUrlFull = computed(() =>
  props.object
    ? buildCheckmkUrl(props.object, props.checkmkUrl ?? null, props.state?.site_id)
    : null
)

// A site drawer's one action is Checkmk's service-problems view scoped to that
// site. Its own defaults (CRIT/WARN/UNKN) are exactly what is wanted here, so
// only the scope is passed.
const siteProblemsUrl = computed(() => {
  if (props.object?.type !== 'site' || !props.checkmkUrl) {
    return null
  }
  const siteId = props.object.host_name ?? props.state?.site_id
  if (!siteId) {
    return null
  }
  const params = new URLSearchParams({ view_name: 'svcproblems', site: siteId })
  return `${stripCheckmkBase(props.checkmkUrl)}/check_mk/view.py?${params}`
})

const showContextTab = computed(() => hasContextFacts(details.value, _t))
const showActivityTab = computed(() => activityCount(details.value) > 0)

const activeTab = ref('status')

// A different object may not have the tab the previous one was read on, and
// landing on an empty pane reads as a broken drawer.
watch([() => props.object?.host_name, () => props.object?.service_description], () => {
  activeTab.value = 'status'
})

// Focus moves in on open and back out on close, so a keyboard user lands in the
// drawer and returns to the object they opened it from.
const drawer = useTemplateRef<HTMLElement>('drawer')
let lastFocused: HTMLElement | null = null
watch(
  () => !!props.object,
  async (isOpen) => {
    if (isOpen) {
      lastFocused = document.activeElement instanceof HTMLElement ? document.activeElement : null
      await nextTick()
      drawer.value?.focus()
    } else {
      lastFocused?.focus()
      lastFocused = null
    }
  },
  { immediate: true }
)

const accentStyle = computed(() => ({
  '--maps-detail-drawer-accent': props.state
    ? stateColorVar(props.state.state)
    : 'var(--default-border-color)'
}))
</script>

<template>
  <Transition
    enter-from-class="maps-detail-drawer__slide-enter-from"
    enter-active-class="maps-detail-drawer__slide-enter-active"
    leave-to-class="maps-detail-drawer__slide-leave-to"
    leave-active-class="maps-detail-drawer__slide-leave-active"
  >
    <aside
      v-if="object"
      ref="drawer"
      class="maps-detail-drawer"
      :class="`maps-detail-drawer--${severityKind}`"
      :style="accentStyle"
      :aria-label="displayName"
      tabindex="-1"
      @click.stop
      @keydown.esc="emit('close')"
    >
      <div class="maps-detail-drawer__severity-bar" />

      <DetailHeader
        :name="displayName"
        :type-label="typeLabel"
        :state="state"
        :since="sinceText(state, nowMs, _t)"
        :checkmk-url="checkmkUrlFull"
        :setup-url="checkmkSetupUrlFull"
        @close="emit('close')"
      />

      <div v-if="state" class="maps-detail-drawer__body">
        <CmkTabs v-model="activeTab" class="maps-detail-drawer__tabs">
          <template #tabs>
            <CmkTab id="status">{{ _t('Status') }}</CmkTab>
            <CmkTab v-if="showPerformanceTab" id="performance">{{ _t('Performance') }}</CmkTab>
            <CmkTab v-if="showContextTab" id="context">{{ _t('Context') }}</CmkTab>
            <CmkTab v-if="isGroup" id="members">
              <span class="maps-detail-drawer__tab-with-count">
                {{ _t('Members') }}
                <span class="maps-detail-drawer__tab-count">{{ groupMembers.length }}</span>
              </span>
            </CmkTab>
            <CmkTab v-if="showActivityTab" id="activity">
              <span class="maps-detail-drawer__tab-with-count">
                {{ _t('Activity') }}
                <span class="maps-detail-drawer__tab-count">{{ activityCount(details) }}</span>
              </span>
            </CmkTab>
          </template>

          <template #tab-contents>
            <CmkTabContent id="status" spacing="none">
              <DetailStatusTab
                :object="object"
                :state="state"
                :details="details"
                :display-name="displayName"
                :checkmk-url="checkmkUrl"
                :host-chips="hostChips"
                :service-chips="serviceChips"
                :service-chips-label="serviceChipsLabel"
                :now-ms="nowMs"
              >
                <template #aggregation>
                  <DetailAggregationSection
                    v-if="aggregationSummary"
                    :summary="aggregationSummary"
                    :chips="activeChips"
                    :view="aggregationView"
                    :view-options="aggregationViewOptions"
                    :can-switch-view="(object.expand_depth ?? 0) > 0"
                    :rows="aggregationListRows"
                    :multi-host="aggregationListMultiHost"
                    :problem-leaf-count="aggregationProblemLeaves.length"
                    :can-acknowledge="canCommand('acknowledge')"
                    :stale="state.stale === true"
                    @update:view="setAggregationView"
                    @pick-leaf="onAggregationLeafClick"
                    @bulk-acknowledge="onBulkAcknowledgeClick"
                  />
                </template>
              </DetailStatusTab>
            </CmkTabContent>

            <CmkTabContent v-if="showPerformanceTab" id="performance" spacing="none">
              <DetailPerformanceTab
                :headline="mainHeadline"
                :headline-row="mainPerfRow"
                :history-data="historyData"
                :history-key="mainHistoryKey"
                :history-thresholds="mainThresholds"
                :history-window-secs="HISTORY_MINUTES * 60"
                :headline-unit="mainMetric?.unit"
                :long-output-rows="longOutputRows"
                :other-rows="otherPerfRows"
              />
            </CmkTabContent>

            <CmkTabContent v-if="showContextTab" id="context" spacing="none">
              <DetailContextTab
                :details="details"
                :selectable-hosts="selectableHosts ?? []"
                @select-host="emit('select-host', $event)"
              />
            </CmkTabContent>

            <CmkTabContent v-if="isGroup" id="members" spacing="none">
              <DetailMembersTab
                :members="groupMembers"
                :visible-members="visibleMembers"
                :filtered-count="filteredMembers.length"
                :truncated-count="truncatedMemberCount"
                :loading="loadingMembers"
                :chips="memberChips"
                :search="memberSearch"
                :only-problems="onlyProblems"
                :now-ms="nowMs"
                :state-tone="memberStateTone"
                :state-badge="memberStateBadge"
                @update:search="memberSearch = $event"
                @update:only-problems="onlyProblems = $event"
                @select-member="(host, service) => emit('select-host', host, service)"
              />
            </CmkTabContent>

            <CmkTabContent v-if="showActivityTab" id="activity" spacing="none">
              <DetailActivityTab :details="details" :now-ms="nowMs" />
            </CmkTabContent>
          </template>
        </CmkTabs>
      </div>

      <!-- An aggregation gets no command footer: the commands dispatch by host
           and service, which a BI aggregation does not have, so every button
           would be a silent no-op. Its own pane offers the one command that
           does apply -- acknowledging the real leaves underneath. -->
      <DetailActions
        v-if="!isSite && !isAggregation"
        :state="state"
        :problematic="isProblemState(state)"
        :is-group="isGroup"
        :member-count="groupMembers.length"
        :can="canCommand"
        @acknowledge="emit('acknowledge')"
        @remove-ack="emit('remove-ack')"
        @force-check="emit('force-check')"
        @schedule-downtime="emit('schedule-downtime')"
        @remove-downtime="emit('remove-downtime')"
        @add-comment="emit('add-comment')"
        @enable-notifications="emit('enable-notifications')"
        @disable-notifications="emit('disable-notifications')"
      />

      <footer v-else-if="isSite && siteProblemsUrl" class="maps-detail-drawer__site-actions">
        <CmkButton
          variant="success"
          :href="siteProblemsUrl"
          target="_blank"
          rel="noopener noreferrer"
        >
          {{ _t('Show problems') }}
        </CmkButton>
      </footer>
    </aside>
  </Transition>
</template>

<style scoped>
.maps-detail-drawer {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;

  /* Above everything drawn on the map, Leaflet's own controls included. */
  z-index: var(--z-index-modal);
  display: flex;
  flex-direction: column;
  width: min(360px, 100%);
  box-sizing: border-box;
  border-left: 4px solid var(--maps-detail-drawer-accent);
  background: var(--default-bg-color);

  &:focus {
    outline: none;
  }
}

.maps-detail-drawer__slide-enter-active,
.maps-detail-drawer__slide-leave-active {
  transition:
    opacity 0.2s ease-in-out,
    transform 0.2s ease-in-out;
}

.maps-detail-drawer__slide-enter-from,
.maps-detail-drawer__slide-leave-to {
  opacity: 0;
  transform: translateX(50%);
}

/* The state, said once more in colour alone: readable from across the room,
   which is how a drawer left open on a wall display gets read. */
.maps-detail-drawer__severity-bar {
  height: 3px;
  flex-shrink: 0;
  background: var(--maps-detail-drawer-accent);
}

.maps-detail-drawer__body {
  flex: 1 1 auto;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.maps-detail-drawer__tabs {
  flex: 1 1 auto;
  min-height: 0;
}

.maps-detail-drawer__tab-with-count {
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-3);
}

.maps-detail-drawer__tab-count {
  background: color-mix(in srgb, var(--color-state-warning) 20%, transparent);
  color: var(--font-color);
  font-size: 9px;
  line-height: 14px;
  min-width: 16px;
  padding: 0 4px;
  border-radius: 999px;
  text-align: center;
  font-weight: var(--font-weight-bold);
}

.maps-detail-drawer__site-actions {
  border-top: 1px solid var(--default-border-color);
  padding: 12px 16px;
  flex-shrink: 0;
  background: var(--ux-theme-3);
}
</style>
