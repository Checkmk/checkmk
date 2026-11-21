<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The card over a group of hosts the flow map draws as one, a collapsed group or
a site: its hosts and their services by state, as a host group's card counts
them, and which hosts to look at first, each of which opens its slide-in.
-->
<script setup lang="ts">
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, nextTick, ref } from 'vue'

import HoverCard from '@/maps/map/components/HoverCard.vue'
import HoverCardHeadline from '@/maps/map/components/HoverCardHeadline.vue'
import MapStateCounts, { type StateCountTone } from '@/maps/map/components/MapStateCounts.vue'
import type { Attention } from '@/maps/map/flow/attention'
import type { FoldHost } from '@/maps/map/flow/nodes'
import type { ServicesSummary } from '@/maps/types/api'
import type { AnchorRect } from '@/maps/utils/anchorRect'
import { buildHostStateViewUrl, buildServiceStateViewUrl } from '@/maps/utils/mapNavigation'
import { stateCountWordFromToken } from '@/maps/utils/objectAria'
import { usePointerOverlayStyle } from '@/maps/utils/overlayFrame'
import { summaryStateCounts } from '@/maps/utils/stateCounts'

export interface GroupCardContent {
  name: string
  subtitle: string
  state: string
  summary: { hosts: ServicesSummary; services: ServicesSummary }
  /** What the counts link to in Checkmk's views: a site, or the group's hosts. */
  viewTarget: { site?: string | null; hosts?: string[] }
  /** The hosts that need attention, the most urgent first: some of them, where there are many. */
  pressing: FoldHost[]
  /** How many hosts need attention in all. */
  pressingCount: number
  /** Why the group's hosts are unreachable, where a host down above them is the cause. */
  cause?: string | null
  /** That host, which the cause opens. */
  causeHost?: string | null
}

const props = defineProps<{
  content: GroupCardContent
  /** Where the card opens, in viewport coordinates, and the group it belongs to. */
  x: number
  y: number
  around: AnchorRect
  checkmkUrl: string | null
}>()

const emit = defineEmits<{
  'card-enter': []
  'card-leave': []
  /** Escape in the card: back to the group it belongs to. */
  back: []
  'select-host': [hostName: string]
}>()

const { _t, _tn } = usei18n()

const rows = computed(() =>
  [
    {
      label: _t('Hosts'),
      counts: summaryStateCounts(_t, props.content.summary.hosts, 'hosts', (state) =>
        buildHostStateViewUrl(props.checkmkUrl, props.content.viewTarget, state)
      )
    },
    {
      label: _t('Services'),
      counts: summaryStateCounts(_t, props.content.summary.services, 'services', (state) =>
        buildServiceStateViewUrl(props.checkmkUrl, props.content.viewTarget, state)
      )
    }
  ].filter((row) => row.counts.some((entry) => entry.count > 0))
)

/** How many hosts the card names until the operator asks for all. */
/**
 * The cause around the host it names, which is kept on one line: a name broken
 * at a dash reads as two.
 */
const causeParts = computed(() => {
  const { cause, causeHost } = props.content
  if (!cause || !causeHost) {
    return null
  }
  const at = cause.indexOf(causeHost)
  return at < 0
    ? { before: cause, host: '', after: '' }
    : {
        before: cause.slice(0, at),
        host: causeHost,
        after: cause.slice(at + causeHost.length)
      }
})

const FIRST = 3

const showsAll = ref(false)
const listed = computed(() =>
  showsAll.value ? props.content.pressing : props.content.pressing.slice(0, FIRST)
)
const more = computed(() => props.content.pressing.length - listed.value.length)
/** Those the card does not list even in full, which the counts above link to. */
const unlisted = computed(() =>
  showsAll.value ? props.content.pressingCount - props.content.pressing.length : 0
)

const TONE: Partial<Record<Attention, StateCountTone>> = {
  down: 'crit',
  critical: 'crit',
  unreachable: 'unknown',
  unknown: 'unknown',
  warning: 'warn'
}

/** Why a host is listed, so a host with service problems does not read as down. */
function reason(needs: Attention): string {
  switch (needs) {
    case 'down':
      return stateCountWordFromToken(_t, 'DOWN')
    case 'unreachable':
      return stateCountWordFromToken(_t, 'UNREACHABLE')
    case 'critical':
      return _t('CRIT services')
    case 'unknown':
      return _t('UNKNOWN services')
    case 'warning':
      return _t('WARN services')
    default:
      return ''
  }
}

const rootEl = ref<HTMLDivElement | null>(null)
const positionStyle = usePointerOverlayStyle(
  rootEl,
  () => ({ x: props.x, y: props.y }),
  () => props.around
)

/** Focus leaving the card closes it, as the pointer leaving it does. */
function onFocusOut(event: FocusEvent): void {
  // No target is focus dropped where it was, such as by a button that went away.
  const to = event.relatedTarget
  if (to instanceof Node && !rootEl.value?.contains(to)) {
    emit('card-leave')
  }
}

/** Lists every host, keyboard focus on the first one it adds. */
async function showAll(): Promise<void> {
  showsAll.value = true
  await nextTick()
  rootEl.value
    ?.querySelectorAll<HTMLButtonElement>('.maps-flow-group-hover-card__host')
    [FIRST]?.focus()
}

defineExpose({
  /** Moves keyboard focus to the card's first link or button; false if it has none. */
  focusFirst(): boolean {
    const first = rootEl.value?.querySelector<HTMLElement>('a[href], button')
    first?.focus()
    return Boolean(first)
  }
})
</script>

<template>
  <div
    ref="rootEl"
    class="maps-flow-group-hover-card"
    :style="positionStyle"
    @focusin="emit('card-enter')"
    @focusout="onFocusOut"
    @keydown.escape.stop="emit('back')"
  >
    <HoverCard @card-enter="emit('card-enter')" @card-leave="emit('card-leave')">
      <HoverCardHeadline :name="content.name" :subtitle="content.subtitle" :state="content.state" />
      <!-- First: it is the one thing an operator looking at this group needs to know. -->
      <button
        v-if="causeParts && content.causeHost"
        type="button"
        class="maps-flow-group-hover-card__cause"
        @click="emit('select-host', content.causeHost)"
      >
        {{ causeParts.before
        }}<span class="maps-flow-group-hover-card__cause-host">{{ causeParts.host }}</span
        >{{ causeParts.after }}
      </button>
      <MapStateCounts
        v-for="row in rows"
        :key="row.label"
        class="maps-flow-group-hover-card__counts"
        :label="row.label"
        :counts="row.counts"
      />
      <div v-if="content.pressingCount" class="maps-flow-group-hover-card__first">
        <!-- The count the group's badge shows, which is of hosts, not of services. -->
        <CmkHeading type="h4">{{
          _tn('%{n} host needs attention', '%{n} hosts need attention', content.pressingCount, {
            n: content.pressingCount
          })
        }}</CmkHeading>
        <ul
          class="maps-flow-group-hover-card__hosts"
          :class="{ 'maps-flow-group-hover-card__hosts--all': showsAll }"
        >
          <li v-for="host in listed" :key="host.name">
            <button
              type="button"
              class="maps-flow-group-hover-card__host"
              :title="host.name"
              :aria-label="
                _t('%{host}, %{reason}', { host: host.name, reason: reason(host.needs) })
              "
              @click="emit('select-host', host.name)"
            >
              <span
                class="maps-flow-group-hover-card__dot"
                :class="`maps-flow-group-hover-card__dot--${TONE[host.needs]}`"
              ></span>
              <span class="maps-flow-group-hover-card__name">{{ host.name }}</span>
              <span class="maps-flow-group-hover-card__reason">{{ reason(host.needs) }}</span>
            </button>
          </li>
          <li v-if="more">
            <button
              type="button"
              class="maps-flow-group-hover-card__host maps-flow-group-hover-card__more"
              @click="showAll"
            >
              {{ _tn('Show %{n} more', 'Show %{n} more', more, { n: more }) }}
            </button>
          </li>
          <li v-if="unlisted" class="maps-flow-group-hover-card__unlisted">
            {{ _tn('and %{n} more', 'and %{n} more', unlisted, { n: unlisted }) }}
          </li>
        </ul>
      </div>
    </HoverCard>
  </div>
</template>

<style scoped>
.maps-flow-group-hover-card {
  position: fixed;
  z-index: 50;
  width: max-content;
  max-width: calc(100% - 16px);
  pointer-events: none;
}

.maps-flow-group-hover-card__counts,
.maps-flow-group-hover-card__cause,
.maps-flow-group-hover-card__first {
  margin-top: var(--dimension-5);
}

.maps-flow-group-hover-card__unlisted {
  padding: var(--dimension-2) var(--dimension-3);
  color: var(--font-color-dimmed);
}

.maps-flow-group-hover-card__more {
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
}

.maps-flow-group-hover-card__cause {
  display: block;
  width: 100%;
  margin-bottom: 0;
  padding: 0;
  border: none;
  background: transparent;
  color: var(--font-color);
  font: inherit;
  font-weight: var(--font-weight-medium);
  text-align: left;
  text-decoration: underline;
  cursor: pointer;
}

.maps-flow-group-hover-card__cause-host {
  white-space: nowrap;
}

.maps-flow-group-hover-card__cause:focus-visible {
  outline: revert;
}

/* All of a large group's hosts scroll inside the card rather than past the screen. */
.maps-flow-group-hover-card__hosts--all {
  /* About eight hosts, so the card stays clear of the map's top bar at 800px. */
  max-height: 168px;
  overflow-y: auto;
}

.maps-flow-group-hover-card__hosts {
  margin: var(--dimension-3) 0 0;
  padding: 0;
  list-style: none;
}

.maps-flow-group-hover-card__host {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
  width: 100%;
  padding: var(--dimension-2) var(--dimension-3);
  margin: 0;
  border: none;
  border-radius: var(--border-radius);
  background: transparent;
  color: var(--font-color);
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.maps-flow-group-hover-card__host:hover {
  background: var(--input-hover-bg-color);
}

.maps-flow-group-hover-card__host:focus-visible {
  outline: revert;
  outline-offset: -2px;
}

.maps-flow-group-hover-card__dot {
  flex-shrink: 0;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.maps-flow-group-hover-card__dot--crit {
  background: var(--color-state-critical);
}

.maps-flow-group-hover-card__dot--warn {
  background: var(--color-state-warning);
}

.maps-flow-group-hover-card__dot--unknown {
  background: var(--color-state-unknown);
}

.maps-flow-group-hover-card__name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.maps-flow-group-hover-card__reason {
  flex-shrink: 0;
  margin-left: auto;
  font-size: var(--font-size-normal);
  color: var(--font-color-dimmed);
}
</style>
