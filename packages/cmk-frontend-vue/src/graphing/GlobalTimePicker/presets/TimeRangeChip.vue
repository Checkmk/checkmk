<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkChip from 'cmk-ui-library/components/CmkChip.vue'
import { computed } from 'vue'

const props = defineProps<{
  selected: boolean
  /** Render as a `<div>` (no button) when nested inside another focusable control. */
  asDiv?: boolean
}>()

defineEmits<{ click: [] }>()

const NEUTRAL_FILL = {
  '--chip-color': 'var(--default-button-optional-color)',
  '--chip-fill-font-color': 'var(--font-color)',
  '--chip-fill-hover-color': 'var(--font-color)',
  '--chip-fill-hover-opacity': '0.1'
} as const

const chipStyle = computed(() => ({
  '--chip-border-color': 'var(--button-optional-border-color)',
  ...(props.selected ? { '--font-color': 'var(--black)' } : NEUTRAL_FILL)
}))
</script>

<template>
  <CmkChip
    variant="fill"
    color="success"
    class="graphing-time-range-chip"
    :as-div="asDiv"
    :aria-pressed="asDiv ? undefined : selected"
    :style="chipStyle"
    @click="$emit('click')"
  >
    <slot />
  </CmkChip>
</template>

<style scoped>
.graphing-time-range-chip {
  text-wrap: nowrap;
}
</style>
