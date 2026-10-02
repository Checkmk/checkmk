<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import type { StatsPart } from '@/dashboard/types/widget'

import { STATE_HEXAGON_STYLE, hexagonPath, nestedRings } from './hexagon'

export interface StateRingPart {
  category: StatsPart['category']
  count: number
}

const props = defineProps<{
  parts: readonly StateRingPart[]
  radius: number
  ringLabel: ((part: StateRingPart) => string) | null
}>()

const rings = computed(() =>
  nestedRings(props.parts, props.radius)
    .filter(({ part }) => part.count > 0)
    .map(({ part, radius }) => ({
      category: part.category,
      path: hexagonPath(radius),
      style: STATE_HEXAGON_STYLE[part.category],
      label: props.ringLabel === null ? null : props.ringLabel(part)
    }))
)
</script>

<template>
  <path
    v-for="ring in rings"
    :key="ring.category"
    :role="ring.label === null ? undefined : 'img'"
    :aria-label="ring.label ?? undefined"
    :d="ring.path"
    :fill="ring.style.color"
    :fill-opacity="ring.style.fillOpacity"
    :stroke="ring.style.color"
    :stroke-opacity="ring.style.strokeOpacity"
  />
</template>
