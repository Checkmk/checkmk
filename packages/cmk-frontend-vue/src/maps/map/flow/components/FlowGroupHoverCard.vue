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
import { computed, ref } from 'vue'

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
  /** The hosts to look at first, a few at most. */
  first: FoldHost[]
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
  'select-host': [hostName: string]
}>()

const { _t } = usei18n()

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
</script>

<template>
  <div ref="rootEl" class="maps-flow-group-hover-card" :style="positionStyle">
    <HoverCard @card-enter="emit('card-enter')" @card-leave="emit('card-leave')">
      <HoverCardHeadline :name="content.name" :subtitle="content.subtitle" :state="content.state" />
      <MapStateCounts
        v-for="row in rows"
        :key="row.label"
        class="maps-flow-group-hover-card__counts"
        :label="row.label"
        :counts="row.counts"
      />
      <div v-if="content.first.length" class="maps-flow-group-hover-card__first">
        <CmkHeading type="h4">{{ _t('Unhandled problems') }}</CmkHeading>
        <ul class="maps-flow-group-hover-card__hosts">
          <li v-for="host in content.first" :key="host.name">
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
.maps-flow-group-hover-card__first {
  margin-top: var(--dimension-5);
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
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
}
</style>
