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
import HoverPillRow, { type HoverPill, type PillTone } from '@/maps/map/components/HoverPillRow.vue'
import type { FolderTreeNode } from '@/maps/types/api'
import { usePointerOverlayStyle } from '@/maps/utils/overlayFrame'

const props = defineProps<{
  folder: FolderTreeNode
  /** What a click on the tile does, or null when it does nothing. */
  clickHint: string | null
  /** The pointer, in viewport coordinates. */
  x: number
  y: number
}>()

const emit = defineEmits<{
  'card-enter': []
  'card-leave': []
}>()

const { _t, _tn } = usei18n()

/** Where the card opens: off the pointer, so it does not sit under it. */
const POINTER_OFFSET = 12

// A folder's hosts by their worst state, in the words and order of the host card.
const HOST_PILLS: { state: string; label: string; tone: PillTone }[] = [
  { state: 'CRITICAL', label: 'CRIT', tone: 'crit' },
  { state: 'DOWN', label: 'DOWN', tone: 'crit' },
  { state: 'UNKNOWN', label: 'UNKN', tone: 'unknown' },
  { state: 'UNREACHABLE', label: 'UNRCH', tone: 'unknown' },
  { state: 'WARNING', label: 'WARN', tone: 'warn' },
  { state: 'PENDING', label: 'PEND', tone: 'pending' }
]

const pills = computed<HoverPill[]>(() => {
  const counts = props.folder.severity_counts
  const problems = HOST_PILLS.filter(({ state }) => (counts[state] ?? 0) > 0).map(
    ({ state, label, tone }) => ({ label, tone, count: counts[state] ?? 0, url: null })
  )
  const counted = problems.reduce((sum, pill) => sum + pill.count, 0)
  const healthy = Math.max(0, props.folder.host_count - counted)
  return healthy > 0
    ? [...problems, { label: 'OK', tone: 'ok', count: healthy, url: null }]
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
      <HoverPillRow v-if="pills.length" :label="_t('Hosts')" :pills="pills" />
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
  margin-top: var(--spacing);
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
}
</style>
