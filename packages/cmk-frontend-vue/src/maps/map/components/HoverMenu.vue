<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { type CSSProperties, computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'

import { useMetricInfo } from '@/maps/map/composables/useMetricInfo'
import type { HoverAnchorRect } from '@/maps/map/composables/useObjectHoverMenu'
import { displayRows, perfometerCaption } from '@/maps/map/composables/usePerfometer'
import { useMapsApis } from '@/maps/services/context'
import type { MapElement, ObjectState, ServicesSummary } from '@/maps/types/api'
import { objectTypeLabel } from '@/maps/utils/dropdownOptions'
import {
  buildHostStateViewUrl,
  buildServiceStateViewUrl,
  summarySubject
} from '@/maps/utils/mapNavigation'
import {
  VISUAL_ONLY_TYPES,
  getEffectiveObjectType,
  getMapElementIdentifier
} from '@/maps/utils/naming'
import { overlayFrameOf } from '@/maps/utils/overlayFrame'
import { type PerfMetric, parsePerfData, utilColor, utilPercent } from '@/maps/utils/perf'
import { sanitizeTemplateHtml } from '@/maps/utils/sanitize'
import { interpolateTemplate } from '@/maps/utils/template'
import { formatRelativeDuration, formatRelativeFuture } from '@/maps/utils/time'

const props = defineProps<{
  object: MapElement
  state: ObjectState | undefined
  x: number
  y: number
  template?: string | null
  connectionId?: string | null
  // Checkmk GUI base — makes the service-state pills clickable links into
  // the filtered allservices view. Omit (standalone) for plain pills.
  checkmkUrl?: string | null
  // Bounding rect of the hovered icon (in viewport coords). When the tooltip
  // has to flip to avoid overflow we anchor the flipped position at this
  // rect's edges so the tooltip never lands on top of the icon.
  anchorRect?: HoverAnchorRect | null
}>()

// Drives the close-grace in the host views (see ``useHoverGrace``). Emitted
// from mouseenter, NOT pointerenter: pointer events fire first, so a
// pointerenter-cancel would run before the object's mouseleave schedules the
// close and the timer would survive.
const emit = defineEmits<{
  'card-enter': []
  'card-leave': []
}>()

// Frozen while the pointer is on the card: the parent keeps emitting hover
// coordinates, which would yank it from under the cursor mid-click.
const pinned = ref(false)
function onCardEnter() {
  pinned.value = true
  emit('card-enter')
}
function onCardLeave() {
  pinned.value = false
  emit('card-leave')
}

const { _t } = usei18n()
const { objects } = useMapsApis()

// ``pending`` hides the raw perf_data fallback while the CMK perfometer is
// still loading, so the tooltip does not flicker between two bar styles.
const isServiceLinked = computed(
  () =>
    props.object.type === 'service' ||
    ((props.object.type === 'line' || props.object.type === 'graph') &&
      !!props.object.service_description)
)
const { info: cmkMetricInfo, pending: cmkPerfometerPending } = useMetricInfo({
  connectionId: () => props.connectionId,
  hostName: () => props.object.host_name,
  serviceDescription: () => props.object.service_description,
  perfData: () => props.state?.perf_data,
  checkCommand: () => props.state?.check_command,
  enabled: () =>
    isServiceLinked.value &&
    // No perfdata to resolve when the service doesn't exist or we're locked out.
    props.state?.state !== 'NOT_FOUND' &&
    props.state?.state !== 'NO_PERMISSION'
})
const cmkPerfometer = computed(() => cmkMetricInfo.value?.perfometer ?? null)

// Member host names for a (non-bundle) dyngroup, fetched lazily so its pills
// can deep-link to a host_regex-filtered Checkmk view. Bundles already carry
// bundle_hosts, so they skip this.
const dyngroupMemberHosts = ref<string[] | null>(null)

// Rendered invisible once to measure, then flipped to the cursor's left/top
// side where it would overflow the frame. It is measured at the frame's origin:
// placed near the right edge it would shrink to the room left there and the
// flip would reckon with a narrower card than the one it then shows.
const rootEl = ref<HTMLDivElement | null>(null)
const adjusted = ref<{ left: number; top: number; ready: boolean }>({
  left: 0,
  top: 0,
  ready: false
})

const positionStyle = computed<CSSProperties>(() =>
  adjusted.value.ready
    ? { left: `${adjusted.value.left}px`, top: `${adjusted.value.top}px` }
    : { left: '0px', top: '0px', visibility: 'hidden' }
)

// Inside Checkmk's <iframe name="main"> the outer window is often smaller than
// the iframe's own innerHeight, so a position that fits `window.innerHeight`
// can still paint past the visible parent edge.
function getEffectiveBounds(): { width: number; height: number } {
  const fallback = { width: window.innerWidth, height: window.innerHeight }
  if (window === window.top) {
    return fallback
  }
  try {
    const top = window.top
    const frame = window.frameElement as HTMLIFrameElement | null
    if (!top || !frame) {
      return fallback
    }
    const fr = frame.getBoundingClientRect()
    return {
      width: Math.min(fallback.width, top.innerWidth - fr.left),
      height: Math.min(fallback.height, top.innerHeight - fr.top)
    }
  } catch {
    return fallback
  }
}

async function updatePosition() {
  await nextTick()
  if (!rootEl.value) {
    return
  }
  const rect = rootEl.value.getBoundingClientRect()
  const frame = overlayFrameOf(rootEl.value)
  const visible = getEffectiveBounds()
  const right = Math.min(frame.right, visible.width)
  const bottom = Math.min(frame.bottom, visible.height)
  const margin = 8
  const gap = 8
  let left = props.x
  let top = props.y
  if (left + rect.width > right - margin) {
    // Flip past the icon's *left edge* if we know it; otherwise back off
    // from the cursor by the tooltip width. Cursor-based fallback can
    // overlap a small icon, so anchorRect is strongly preferred.
    const flipFrom = props.anchorRect ? props.anchorRect.left : props.x
    left = Math.max(frame.left + margin, flipFrom - rect.width - gap)
  }
  if (top + rect.height > bottom - margin) {
    const flipFrom = props.anchorRect ? props.anchorRect.top : props.y
    top = Math.max(frame.top + margin, flipFrom - rect.height - gap)
  }
  adjusted.value = { left: left - frame.left, top: top - frame.top, ready: true }
}

watch(
  () => [props.x, props.y],
  () => {
    // Frozen while the pointer is on the card — repositioning would yank
    // the pill out from under the cursor mid-click.
    if (pinned.value) {
      return
    }
    adjusted.value.ready = false
    void updatePosition()
  }
)

onMounted(() => {
  void updatePosition()
})

onMounted(() => {
  if (
    props.object.type === 'dyngroup' &&
    !props.object.bundle_hosts?.length &&
    props.object.object_filter &&
    props.connectionId &&
    props.checkmkUrl
  ) {
    objects
      .fetchDyngroupMembers(props.object.object_types ?? 'host', props.object.object_filter)
      .then((rows) => {
        dyngroupMemberHosts.value = [...new Set(rows.map((r) => r.host).filter(Boolean))]
      })
      .catch(() => {})
  }
})

const renderedTemplate = computed(() => {
  if (!props.template) {
    return null
  }
  const html = interpolateTemplate(props.template, props.object, props.state)
  return sanitizeTemplateHtml(html)
})

const displayName = computed(() => getMapElementIdentifier(props.object) ?? '')

const hoverTypeLabel = computed(() => objectTypeLabel(getEffectiveObjectType(props.object), _t))

const hasMonitoring = computed(() => {
  // A line linked to a host/service is not purely decorative — show its state.
  if (props.object.type === 'line') {
    return !!(props.object.host_name || props.object.service_description)
  }
  return !(VISUAL_ONLY_TYPES as readonly string[]).includes(props.object.type)
})

const isNoPermission = computed(() => props.state?.state === 'NO_PERMISSION')
const isNotFound = computed(() => props.state?.state === 'NOT_FOUND')

const STATE_BG: Record<string, string> = {
  UP: 'maps-hover-menu__dot--ok',
  OK: 'maps-hover-menu__dot--ok',
  DOWN: 'maps-hover-menu__dot--down',
  CRITICAL: 'maps-hover-menu__dot--down',
  UNREACHABLE: 'maps-hover-menu__dot--unknown',
  UNKNOWN: 'maps-hover-menu__dot--unknown',
  WARNING: 'maps-hover-menu__dot--warn',
  PENDING: 'maps-hover-menu__dot--pending'
}
const STATE_TEXT: Record<string, string> = {
  UP: 'maps-hover-menu__state--ok',
  OK: 'maps-hover-menu__state--ok',
  DOWN: 'maps-hover-menu__state--down',
  CRITICAL: 'maps-hover-menu__state--down',
  UNREACHABLE: 'maps-hover-menu__state--unknown',
  UNKNOWN: 'maps-hover-menu__state--unknown',
  WARNING: 'maps-hover-menu__state--warn',
  PENDING: 'maps-hover-menu__state--pending'
}

const stateColor = computed(
  () => STATE_BG[props.state?.state ?? 'PENDING'] ?? 'maps-hover-menu__dot--pending'
)
const stateTextColor = computed(
  () => STATE_TEXT[props.state?.state ?? 'PENDING'] ?? 'maps-hover-menu__state--pending'
)

const subtitleText = computed(() => {
  const parts: string[] = [hoverTypeLabel.value]
  const seen = new Set<string>([displayName.value])
  const push = (raw: string | undefined | null, prefix = '') => {
    const v = raw?.trim()
    if (!v || seen.has(v)) {
      return
    }
    seen.add(v)
    parts.push(prefix ? `${prefix}${v}` : v)
  }
  // alias and address help identify the host beyond the (possibly customised)
  // displayName; site is shown last as a "@site" suffix so it reads naturally
  // ("host · 10.0.4.12 · @eu_west").
  push(props.state?.alias)
  push(props.state?.address)
  push(props.state?.site_id, '@')
  return parts.join(' · ')
})

// Reactive clock so "since X" / "next check in X" tick down while the tooltip
// stays open. Driven by a 1-Hz interval that lives only as long as the
// component is mounted, so closed tooltips don't keep timers alive.
const nowMs = ref(Date.now())
let _tick: ReturnType<typeof setInterval> | null = null
onMounted(() => {
  _tick = setInterval(() => {
    nowMs.value = Date.now()
  }, 1000)
})
onUnmounted(() => {
  if (_tick) {
    clearInterval(_tick)
  }
  _tick = null
})

const attemptsBadge = computed(() => {
  const cur = props.state?.current_attempt ?? 0
  const max = props.state?.max_attempts ?? 0
  if (!cur || !max) {
    return ''
  }
  // Steady-state HARD checks don't need to advertise "1/3" — show only when
  // there's something interesting (SOFT progression or non-first attempt).
  if (props.state?.state_type === 'SOFT' || cur > 1) {
    return `${props.state?.state_type ?? ''} ${cur}/${max}`.trim()
  }
  return ''
})

const stateDuration = computed(() =>
  formatRelativeDuration(props.state?.last_state_change, nowMs.value)
)

// SOFT-state escalation gets an amber attention cue.
const attemptsCls = computed(() =>
  props.state?.state_type === 'SOFT' ? 'maps-hover-menu__attempts--soft' : ''
)

interface NextCheckText {
  text: string
  cls: string
}
// CMC's check scheduling can make `next_check` lag behind "now" by a
// second or two even when the check is healthy. Suppress the "overdue"
// label until the LAST check is itself stale by this many seconds.
const OVERDUE_GRACE_SECONDS = 60
const nextCheckText = computed((): NextCheckText | null => {
  const ts = props.state?.next_check
  if (!ts) {
    return null
  }
  const future = formatRelativeFuture(ts, nowMs.value)
  if (future) {
    return {
      text: _t('next check in %{duration}', { duration: future }),
      cls: ''
    }
  }
  // next_check is in the past, which on its own means nothing (see
  // OVERDUE_GRACE_SECONDS) — only a stale last_check makes it overdue.
  const lastCheck = props.state?.last_check
  const sinceLastCheckSec =
    lastCheck && lastCheck > 0 ? Math.floor(nowMs.value / 1000 - lastCheck) : Infinity
  if (sinceLastCheckSec < OVERDUE_GRACE_SECONDS) {
    return null
  }
  const overdue = formatRelativeDuration(ts, nowMs.value)
  if (!overdue) {
    return null
  }
  return {
    text: _t('check overdue by %{duration}', { duration: overdue }),
    cls: 'maps-hover-menu__next-check--overdue'
  }
})

interface ServicePill {
  label: string
  count: number
  cls: string
  dot: string
  /** Deep-link into the filtered Checkmk view, or null when not linkable. */
  url: string | null
}

interface PillRow {
  label: string
  pills: ServicePill[]
}

const dyngroupHostSet = computed<string[] | null>(() =>
  props.object.type === 'dyngroup'
    ? props.object.bundle_hosts?.length
      ? props.object.bundle_hosts
      : dyngroupMemberHosts.value
    : null
)

// Severity-descending, so the worst state reads first.
function buildPills(summary: ServicesSummary, kind: 'hosts' | 'services'): ServicePill[] {
  const hosts = dyngroupHostSet.value
  const linkFor = (state: string | null): string | null => {
    if (!state || !props.checkmkUrl) {
      return null
    }
    if (kind === 'hosts') {
      return props.object.type === 'dyngroup' && hosts?.length
        ? buildHostStateViewUrl(props.checkmkUrl, hosts, state)
        : null
    }
    if (props.object.type === 'host') {
      return buildServiceStateViewUrl(props.checkmkUrl, { host: props.object.host_name }, state)
    }
    if (props.object.type === 'dyngroup' && hosts?.length) {
      return buildServiceStateViewUrl(props.checkmkUrl, { hosts }, state)
    }
    return null
  }
  const defs =
    kind === 'hosts'
      ? ([
          { key: 'critical', label: 'DOWN', tone: 'crit', state: 'DOWN' },
          { key: 'unknown', label: 'UNRCH', tone: 'unknown', state: 'UNREACHABLE' },
          { key: 'pending', label: 'PEND', tone: 'pending', state: null },
          { key: 'ok', label: 'UP', tone: 'ok', state: 'UP' }
        ] as const)
      : ([
          { key: 'critical', label: 'CRIT', tone: 'crit', state: 'CRITICAL' },
          { key: 'unknown', label: 'UNKN', tone: 'unknown', state: 'UNKNOWN' },
          { key: 'warning', label: 'WARN', tone: 'warn', state: 'WARNING' },
          { key: 'pending', label: 'PEND', tone: 'pending', state: 'PENDING' },
          { key: 'ok', label: 'OK', tone: 'ok', state: 'OK' }
        ] as const)
  return defs
    .filter((d) => (summary[d.key] ?? 0) > 0)
    .map((d) => ({
      label: d.label,
      count: summary[d.key] ?? 0,
      cls: `maps-hover-menu__pill--${d.tone}`,
      dot: `maps-hover-menu__pill-dot--${d.tone}`,
      url: linkFor(d.state)
    }))
}

// Host dyngroups show two rows (member hosts + their services); everything else
// shows one. ``services_summary`` holds host states for host groups (labelled
// accordingly), services otherwise.
const pillRows = computed<PillRow[]>(() => {
  if (!['host', 'hostgroup', 'servicegroup', 'dyngroup'].includes(props.object.type)) {
    return []
  }
  const rows: PillRow[] = []
  const hs = props.state?.hosts_summary
  if (hs) {
    const pills = buildPills(hs, 'hosts')
    if (pills.length) {
      rows.push({ label: _t('Hosts'), pills })
    }
  }
  const ss = props.state?.services_summary
  if (ss) {
    const kind = summarySubject(props.object)
    const pills = buildPills(ss, kind)
    if (pills.length) {
      rows.push({ label: kind === 'hosts' ? _t('Hosts') : _t('Services'), pills })
    }
  }
  return rows
})

const perfMetrics = computed((): PerfMetric[] => {
  // Same reasoning as `isServiceLinked` above — only service-linked objects have perf data.
  const showPerf =
    props.object.type === 'service' ||
    ((props.object.type === 'line' || props.object.type === 'graph') &&
      !!props.object.service_description)
  if (!showPerf) {
    return []
  }
  return parsePerfData(props.state?.perf_data ?? '').slice(0, 4)
})

function fmtMetricValue(m: PerfMetric): string {
  const v = Number.isInteger(m.value) ? String(m.value) : m.value.toFixed(2).replace(/\.?0+$/, '')
  return `${v}${m.unit}`
}
</script>

<template>
  <div ref="rootEl" class="maps-hover-menu" :style="positionStyle">
    <div class="maps-hover-menu__card" @mouseenter="onCardEnter" @mouseleave="onCardLeave">
      <!-- No permission: skip all templates and show only this -->
      <div v-if="isNoPermission" class="maps-hover-menu__empty">
        {{ _t('No permission') }}
      </div>

      <!-- NOT_FOUND: object referenced on the map doesn't exist in monitoring data. -->
      <div v-else-if="isNotFound" class="maps-hover-menu__empty">
        <div class="maps-hover-menu__empty-name">
          {{ displayName }}
        </div>
        {{ _t('Not found in monitoring data') }}
      </div>

      <!-- Custom template — content is sanitized via sanitizeTemplateHtml before rendering -->
      <!-- eslint-disable vue/no-v-html -->
      <div
        v-else-if="renderedTemplate"
        class="maps-hover-menu__template"
        v-html="renderedTemplate"
      />
      <!-- eslint-enable vue/no-v-html -->

      <template v-else>
        <div class="maps-hover-menu__headline">
          <span v-if="hasMonitoring" class="maps-hover-menu__dot" :class="stateColor" />
          <div class="maps-hover-menu__name">
            {{ displayName }}
          </div>
          <span
            v-if="hasMonitoring && state"
            class="maps-hover-menu__state"
            :class="stateTextColor"
          >
            {{ state.state }}
          </span>
          <span v-if="hasMonitoring && state && stateDuration" class="maps-hover-menu__since">
            {{ _t('since %{duration}', { duration: stateDuration }) }}
          </span>
        </div>
        <div class="maps-hover-menu__subtitle">
          {{ subtitleText }}
        </div>

        <template v-if="hasMonitoring">
          <div v-if="state">
            <div v-if="attemptsBadge" class="maps-hover-menu__attempts" :class="attemptsCls">
              {{ attemptsBadge }}
            </div>
            <!-- Modifier badges (ACK / DOWNTIME / STALE / MUTED) — directly
                             under the state so the operator sees "no action needed" or
                             "I won't be paged" before scrolling to output/pills. -->
            <div
              v-if="
                state.acknowledged ||
                state.in_downtime ||
                state.stale ||
                state.notifications_enabled === false
              "
              class="maps-hover-menu__badges"
            >
              <span
                v-if="state.acknowledged"
                class="maps-hover-menu__badge maps-hover-menu__badge--warn"
              >
                <svg
                  class="maps-hover-menu__badge-icon"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  stroke-width="3"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
                {{ _t('ACK') }}
              </span>
              <span
                v-if="state.in_downtime"
                class="maps-hover-menu__badge maps-hover-menu__badge--downtime"
              >
                <svg class="maps-hover-menu__badge-icon" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
                </svg>
                {{ _t('DOWNTIME') }}
              </span>
              <span v-if="state.stale" class="maps-hover-menu__badge maps-hover-menu__badge--stale">
                <svg
                  class="maps-hover-menu__badge-icon"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  stroke-width="2.5"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                {{ _t('STALE') }}
              </span>
              <!-- Critical operator awareness: notifications disabled means
                                 nobody gets paged when this host breaks. Don't let the
                                 operator assume otherwise. -->
              <span
                v-if="state.notifications_enabled === false"
                class="maps-hover-menu__badge maps-hover-menu__badge--warn"
                :title="_t('Notifications disabled — alerts will not be sent for this host')"
              >
                <svg
                  class="maps-hover-menu__badge-icon"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M9.143 17.082a24.248 24.248 0 003.844.148m-3.844-.148a23.856 23.856 0 01-5.455-1.31 8.964 8.964 0 002.3-5.542m3.155 6.852a3 3 0 005.667 1.97m1.965-2.277L21 21M4.5 4.5l15 15"
                  />
                </svg>
                {{ _t('MUTED') }}
              </span>
            </div>
          </div>

          <div v-if="state?.output" class="maps-hover-menu__output">
            {{ state.output }}
          </div>

          <!-- State pills, one labelled row per summary (host dyngroups show
                         both Hosts and Services); each pill deep-links to the
                         matching filtered Checkmk view. -->
          <div v-for="row in pillRows" :key="row.label" class="maps-hover-menu__pills">
            <span class="maps-hover-menu__pills-label">{{ row.label }}</span>
            <component
              :is="pill.url ? 'a' : 'span'"
              v-for="pill in row.pills"
              :key="pill.label"
              class="maps-hover-menu__pill"
              :class="[pill.cls, { 'maps-hover-menu__pill--link': pill.url }]"
              :href="pill.url || undefined"
              :target="pill.url ? '_blank' : undefined"
              :rel="pill.url ? 'noopener noreferrer' : undefined"
            >
              <span class="maps-hover-menu__pill-dot" :class="pill.dot" />
              {{ pill.count }} {{ pill.label }}
            </component>
          </div>

          <div v-if="cmkPerfometer" class="maps-hover-menu__perfometer">
            <div class="maps-hover-menu__perfometer-label">
              {{ perfometerCaption(cmkPerfometer) }}
            </div>
            <div
              v-for="(row, ri) in displayRows(cmkPerfometer)"
              :key="ri"
              class="maps-hover-menu__perfometer-row"
            >
              <div
                v-for="(seg, si) in row"
                :key="si"
                class="maps-hover-menu__perfometer-seg"
                :style="{ width: `${seg.pct}%`, backgroundColor: seg.color }"
              />
            </div>
          </div>

          <!-- Fallback: simple perf_data bars — only when no CMK perfometer is on the way -->
          <div
            v-else-if="!cmkPerfometerPending && perfMetrics.length"
            class="maps-hover-menu__metrics"
          >
            <template v-for="m in perfMetrics" :key="m.label">
              <div class="maps-hover-menu__metric-head">
                <span class="maps-hover-menu__metric-label">{{ m.label }}</span>
                <span class="maps-hover-menu__metric-value">{{ fmtMetricValue(m) }}</span>
              </div>
              <div v-if="utilPercent(m) > 0" class="maps-hover-menu__metric-bar">
                <div
                  class="maps-hover-menu__metric-fill"
                  :style="{
                    width: `${utilPercent(m)}%`,
                    backgroundColor: utilColor(utilPercent(m))
                  }"
                />
              </div>
            </template>
          </div>

          <div v-if="nextCheckText" class="maps-hover-menu__next-check" :class="nextCheckText.cls">
            {{ nextCheckText.text }}
          </div>
        </template>
      </template>
    </div>
  </div>
</template>

<style scoped>
.maps-hover-menu {
  position: fixed;
  z-index: 50;
  pointer-events: none;
}

a.maps-hover-menu__pill {
  cursor: pointer;
  text-decoration: none;
}

a.maps-hover-menu__pill:hover {
  filter: brightness(1.25);
  text-decoration: underline;
}

/* The card is interactive (tooltip stays while the pointer is on it; the
   pills are links). It can overlap neighbouring objects — leaving it
   re-schedules the close so anything underneath becomes hoverable again. */
.maps-hover-menu__card {
  pointer-events: auto;
  min-width: 208px;
  max-width: 288px;
  padding: 14px;
  background: var(--maps-map-view-glass);
  backdrop-filter: blur(12px);
  border-radius: 12px;
  box-shadow:
    0 0 0 1px var(--default-border-color),
    0 25px 50px -12px rgb(0 0 0 / 60%);
}

.maps-hover-menu__empty {
  font-size: var(--font-size-large);
  line-height: 20px;
  font-style: italic;
  color: var(--font-color-dimmed);
}

.maps-hover-menu__empty-name {
  margin-bottom: var(--dimension-3);
  font-style: normal;
  font-weight: var(--font-weight-bold);
  color: var(--font-color);
}

.maps-hover-menu__template {
  /* Holds author- and monitoring-driven markup: without paint containment a
     purely cosmetic style (margin + size) still covers the map and eats clicks. */
  contain: paint;
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--font-color);
}

.maps-hover-menu__headline {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: var(--dimension-4);
}

.maps-hover-menu__dot {
  align-self: center;
  flex-shrink: 0;
  width: 8px;
  height: 8px;
  border-radius: 9999px;
}

.maps-hover-menu__dot--ok {
  background: var(--color-corporate-green-50);
}

.maps-hover-menu__dot--down {
  background: var(--color-light-red-50);
}

.maps-hover-menu__dot--unknown {
  background: var(--color-orange-40);
}

.maps-hover-menu__dot--warn {
  background: var(--color-warning);
}

.maps-hover-menu__dot--pending {
  background: var(--color-state-pending);
}

.maps-hover-menu__name {
  overflow: hidden;
  flex: 1;
  min-width: 0;
  font-size: var(--font-size-large);
  line-height: 1.25;
  font-weight: var(--font-weight-bold);
  color: var(--font-color);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.maps-hover-menu__state {
  flex-shrink: 0;
  font-size: var(--font-size-large);
  line-height: 1.25;
  font-weight: var(--font-weight-bold);
}

.maps-hover-menu__state--ok {
  color: var(--color-corporate-green-60);
}

body[data-theme='modern-dark'] .maps-hover-menu__state--ok {
  color: var(--color-corporate-green-50);
}

.maps-hover-menu__state--down {
  color: var(--color-light-red-60);
}

body[data-theme='modern-dark'] .maps-hover-menu__state--down {
  color: var(--color-light-red-40);
}

.maps-hover-menu__state--unknown {
  color: var(--color-orange-60);
}

body[data-theme='modern-dark'] .maps-hover-menu__state--unknown {
  color: var(--color-orange-40);
}

.maps-hover-menu__state--warn {
  color: var(--color-yellow-60);
}

body[data-theme='modern-dark'] .maps-hover-menu__state--warn {
  color: var(--color-warning);
}

.maps-hover-menu__state--pending {
  color: var(--font-color-dimmed);
}

.maps-hover-menu__since {
  flex-shrink: 0;
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
}

.maps-hover-menu__subtitle {
  overflow: hidden;
  margin-top: var(--dimension-2);
  font-size: var(--font-size-normal);
  line-height: 16px;
  color: var(--font-color-dimmed);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.maps-hover-menu__attempts {
  margin-top: 6px;
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
}

.maps-hover-menu__attempts--soft {
  font-weight: var(--font-weight-bold);
  color: var(--color-yellow-60);
}

body[data-theme='modern-dark'] .maps-hover-menu__attempts--soft {
  color: var(--color-yellow-50);
}

.maps-hover-menu__badges {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
}

.maps-hover-menu__badge {
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-3);
  padding: var(--dimension-2) 6px;
  font-size: var(--font-size-small);
  font-weight: var(--font-weight-bold);
  border-radius: 9999px;
}

.maps-hover-menu__badge--warn {
  color: var(--color-yellow-60);
  background: color-mix(in srgb, var(--color-warning) 20%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-warning) 40%, transparent);
}

body[data-theme='modern-dark'] .maps-hover-menu__badge--warn {
  color: var(--color-yellow-50);
  background: color-mix(in srgb, var(--color-warning) 15%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-warning) 25%, transparent);
}

.maps-hover-menu__badge--downtime {
  color: var(--color-light-blue-70);
  background: color-mix(in srgb, var(--color-light-blue-50) 20%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-light-blue-50) 40%, transparent);
}

body[data-theme='modern-dark'] .maps-hover-menu__badge--downtime {
  color: var(--color-light-blue-50);
  background: color-mix(in srgb, var(--color-light-blue-50) 15%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-light-blue-50) 25%, transparent);
}

.maps-hover-menu__badge--stale {
  color: var(--font-color-dimmed);
  background: color-mix(in srgb, var(--color-state-pending) 20%, transparent);
  box-shadow: 0 0 0 1px var(--default-border-color);
}

.maps-hover-menu__badge-icon {
  width: 10px;
  height: 10px;
}

.maps-hover-menu__output {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  overflow: hidden;
  margin-top: var(--spacing);
  font-size: var(--font-size-normal);
  line-height: 1.375;
  color: var(--font-color-dimmed);
  overflow-wrap: break-word;
}

.maps-hover-menu__pills {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--dimension-3);
  margin-top: var(--spacing);
}

.maps-hover-menu__pills-label {
  font-size: 11px;
  font-weight: var(--font-weight-bold);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--font-color-dimmed);
  margin-right: var(--dimension-2);
}

.maps-hover-menu__pill {
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-3);
  padding: var(--dimension-2) 6px;
  font-size: var(--font-size-small);
  font-weight: var(--font-weight-bold);
  border-radius: 9999px;
}

.maps-hover-menu__pill--crit {
  color: var(--color-light-red-70);
  background: color-mix(in srgb, var(--color-light-red-50) 15%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-light-red-50) 30%, transparent);
}

body[data-theme='modern-dark'] .maps-hover-menu__pill--crit {
  color: var(--color-light-red-40);
}

.maps-hover-menu__pill--unknown {
  color: var(--color-orange-70);
  background: color-mix(in srgb, var(--color-orange-50) 15%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-orange-50) 30%, transparent);
}

body[data-theme='modern-dark'] .maps-hover-menu__pill--unknown {
  color: var(--color-orange-40);
}

.maps-hover-menu__pill--warn {
  color: var(--color-yellow-60);
  background: color-mix(in srgb, var(--color-warning) 15%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-warning) 30%, transparent);
}

body[data-theme='modern-dark'] .maps-hover-menu__pill--warn {
  color: var(--color-yellow-50);
}

.maps-hover-menu__pill--pending {
  color: var(--font-color-dimmed);
  background: color-mix(in srgb, var(--color-state-pending) 15%, transparent);
  box-shadow: 0 0 0 1px var(--default-border-color);
}

.maps-hover-menu__pill--ok {
  color: var(--color-corporate-green-70);
  background: color-mix(in srgb, var(--color-corporate-green-50) 15%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-corporate-green-50) 30%, transparent);
}

body[data-theme='modern-dark'] .maps-hover-menu__pill--ok {
  color: var(--color-corporate-green-50);
}

.maps-hover-menu__pill-dot {
  width: 6px;
  height: 6px;
  border-radius: 9999px;
}

.maps-hover-menu__pill-dot--crit {
  background: var(--color-light-red-50);
}

.maps-hover-menu__pill-dot--unknown {
  background: var(--color-orange-40);
}

.maps-hover-menu__pill-dot--warn {
  background: var(--color-warning);
}

.maps-hover-menu__pill-dot--pending {
  background: var(--color-state-pending);
}

.maps-hover-menu__pill-dot--ok {
  background: var(--color-corporate-green-50);
}

.maps-hover-menu__perfometer {
  margin-top: var(--spacing);
}

.maps-hover-menu__perfometer > * + * {
  margin-top: var(--dimension-3);
}

.maps-hover-menu__perfometer-label {
  margin-bottom: var(--dimension-3);
  font-size: var(--font-size-small);
  font-weight: 500;
  color: var(--font-color);
}

.maps-hover-menu__perfometer-row {
  display: flex;
  overflow: hidden;
  height: 12px;
  border-radius: var(--border-radius);
  box-shadow: 0 0 0 1px rgb(255 255 255 / 10%);
}

.maps-hover-menu__perfometer-seg {
  height: 100%;
  transition: all 0.15s;
}

.maps-hover-menu__metrics {
  margin-top: var(--spacing);
}

.maps-hover-menu__metrics > * + * {
  margin-top: 6px;
}

.maps-hover-menu__metric-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--dimension-3);
  font-size: var(--font-size-small);
}

.maps-hover-menu__metric-label {
  overflow: hidden;
  color: var(--font-color-dimmed);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.maps-hover-menu__metric-value {
  flex-shrink: 0;
  font-weight: 500;
  color: var(--font-color);
}

.maps-hover-menu__metric-bar {
  overflow: hidden;
  height: 6px;
  margin-top: -2px;
  background: var(--input-hover-bg-color);
  border-radius: 9999px;
}

.maps-hover-menu__metric-fill {
  height: 100%;
  border-radius: 9999px;
}

.maps-hover-menu__next-check {
  margin-top: var(--spacing);
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
}

.maps-hover-menu__next-check--overdue {
  color: var(--color-yellow-60);
}

body[data-theme='modern-dark'] .maps-hover-menu__next-check--overdue {
  color: var(--color-yellow-50);
}
</style>
