<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Reserves the width of the widest `variants` string (measured in the actual current font) for the
slotted content, so text that cycles between known values (e.g. AM/PM) does not shift the layout.
The variants are rendered invisibly underneath the content in a single inline-grid cell; an empty
`variants` list makes this a plain inline wrapper.
-->
<script setup lang="ts">
defineProps<{
  /** Candidate strings the content cycles through; the widest reserves the inline size. Empty = no reservation. */
  variants: string[]
}>()

defineSlots<{
  /** The visible content sized to the widest variant. */
  default?: () => unknown
}>()
</script>

<template>
  <span class="cmk-ghost-width">
    <span
      v-for="variant in variants"
      :key="variant"
      class="cmk-ghost-width__ghost"
      aria-hidden="true"
      >{{ variant }}</span
    >
    <slot />
  </span>
</template>

<style scoped>
.cmk-ghost-width {
  display: inline-grid;

  > * {
    grid-area: 1 / 1;
  }

  > :slotted(*) {
    grid-area: 1 / 1;
  }
}

.cmk-ghost-width__ghost {
  visibility: hidden;
  white-space: pre;
  user-select: none;
}
</style>
