<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The treemap's card over a folder tile: its hosts by state and what a click does.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref } from 'vue'

import HoverCard from '@/maps/map/components/HoverCard.vue'
import HoverCardHeadline from '@/maps/map/components/HoverCardHeadline.vue'
import HoverStateCounts, {
  type HoverStateCount,
  type StateCountTone
} from '@/maps/map/components/HoverStateCounts.vue'
import type { FolderTreeNode } from '@/maps/types/api'
import { buildFolderStateViewUrl } from '@/maps/utils/mapNavigation'
import { stateCountWordFromToken } from '@/maps/utils/objectAria'
import { usePointerOverlayStyle } from '@/maps/utils/overlayFrame'
import { severityPills } from '@/maps/utils/stateColors'

const props = defineProps<{
  folder: FolderTreeNode
  /** What a click on the tile does, or null when it does nothing. */
  clickHint: string | null
  /** The pointer, in viewport coordinates. */
  x: number
  y: number
  /** Checkmk GUI base, which makes the counts links into its views. */
  checkmkUrl: string | null
}>()

const emit = defineEmits<{
  'card-enter': []
  'card-leave': []
}>()

const { _t, _tn } = usei18n()

/** Where the card opens: off the pointer, so it does not sit under it. */
const POINTER_OFFSET = 12

// Only the tone is the card's own; the order is the folder tree's.
const TONE: Record<string, StateCountTone> = {
  CRITICAL: 'crit',
  DOWN: 'crit',
  UNKNOWN: 'unknown',
  UNREACHABLE: 'unknown',
  WARNING: 'warn'
}

const counts = computed<HoverStateCount[]>(() => {
  const problems = severityPills(props.folder.severity_counts).map(({ state, count }) => ({
    label: stateCountWordFromToken(_t, state),
    tone: TONE[state] ?? 'pending',
    count,
    // The "all OK" bundle has no folder of its own to filter on.
    url: props.folder.ok_group
      ? null
      : buildFolderStateViewUrl(props.checkmkUrl, props.folder.path, state)
  }))
  const counted = problems.reduce((sum, entry) => sum + entry.count, 0)
  const healthy = Math.max(0, props.folder.host_count - counted)
  return healthy > 0
    ? [
        ...problems,
        { label: stateCountWordFromToken(_t, 'OK'), tone: 'ok' as const, count: healthy, url: null }
      ]
    : problems
})

const hosts = computed(() =>
  _tn('%{n} host', '%{n} hosts', props.folder.host_count, { n: props.folder.host_count })
)

// The "all OK" bundle stands for the healthy hosts of a folder, not a folder.
const subtitle = computed(() => {
  if (props.folder.ok_group) {
    return _t('Healthy hosts')
  }
  return props.folder.is_empty ? _t('Folder · empty') : _t('Folder')
})

const rootEl = ref<HTMLDivElement | null>(null)
const positionStyle = usePointerOverlayStyle(rootEl, () => ({
  x: props.x + POINTER_OFFSET,
  y: props.y + POINTER_OFFSET
}))
</script>

<template>
  <div ref="rootEl" class="maps-folder-hover-card" :style="positionStyle">
    <HoverCard @card-enter="emit('card-enter')" @card-leave="emit('card-leave')">
      <HoverCardHeadline
        :name="folder.title"
        :subtitle="subtitle"
        :state="folder.is_empty ? null : folder.state"
      >
        <span class="maps-folder-hover-card__hosts">{{ hosts }}</span>
      </HoverCardHeadline>
      <HoverStateCounts v-if="counts.length" :label="_t('Hosts')" :counts="counts" />
      <div v-if="clickHint" class="maps-folder-hover-card__hint">{{ clickHint }}</div>
    </HoverCard>
  </div>
</template>

<style scoped>
.maps-folder-hover-card {
  position: fixed;
  z-index: 50;
  width: max-content;
  max-width: calc(100% - 16px);
  pointer-events: none;
}

.maps-folder-hover-card__hosts {
  flex-shrink: 0;
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
}

.maps-folder-hover-card__hint {
  margin-top: var(--dimension-5);
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
}
</style>
