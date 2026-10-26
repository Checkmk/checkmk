<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkTooltip, {
  CmkTooltipContent,
  CmkTooltipTrigger
} from 'cmk-ui-library/components/CmkTooltip'
import { computed, ref, useTemplateRef, watch } from 'vue'

import type { CmkMenuLabelPart } from './types'

// Each truncation step outweighs the next by so much that a part only starts to
// shrink once the parts before it are down to their minimum.
const SHRINK_RATIO = 1000

const { parts, fullLabel, keyboardFocused } = defineProps<{
  parts: CmkMenuLabelPart[]
  fullLabel: string
  keyboardFocused: boolean
}>()

const partElements = useTemplateRef<HTMLElement[]>('part')

const shrinkFactors = computed(() => {
  const orders = [...new Set(parts.map((part) => part.truncateOrder))]
    .filter((order) => order !== undefined)
    .sort((a, b) => b - a)
  return parts.map((part) =>
    part.truncateOrder === undefined ? 0 : SHRINK_RATIO ** orders.indexOf(part.truncateOrder)
  )
})

function isTruncated(): boolean {
  return (partElements.value ?? []).some((element) => element.scrollWidth > element.clientWidth)
}

const hoverOpen = ref(false)
const focusOpen = ref(false)

watch(
  () => keyboardFocused,
  (focused) => {
    focusOpen.value = focused && isTruncated()
  }
)
</script>

<template>
  <CmkTooltip
    :open="hoverOpen || focusOpen"
    @update:open="(open: boolean) => (hoverOpen = open && isTruncated())"
  >
    <CmkTooltipTrigger as-child>
      <span class="cmk-menu-label">
        <template v-for="(part, index) in parts" :key="index">
          <span v-if="index > 0" class="cmk-menu-label__separator"> – </span>
          <span
            ref="part"
            class="cmk-menu-label__part"
            :class="{ 'cmk-menu-label__part--bold': part.bold }"
            :style="{ flexShrink: shrinkFactors[index] }"
            >{{ part.text }}</span
          >
        </template>
      </span>
    </CmkTooltipTrigger>
    <CmkTooltipContent side="top" align="start" :avoid-collisions="true" use-portal>
      {{ fullLabel }}
    </CmkTooltipContent>
  </CmkTooltip>
</template>

<style scoped>
.cmk-menu-label {
  display: flex;
  flex: 1 1 auto;
  min-width: 0;
}

.cmk-menu-label__separator {
  flex: none;
  white-space: pre;
}

/* A floor of two characters keeps the ellipsis of a fully shortened part visible. */
.cmk-menu-label__part {
  min-width: 2ch;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cmk-menu-label__part--bold {
  font-weight: var(--font-weight-bold);
}
</style>
