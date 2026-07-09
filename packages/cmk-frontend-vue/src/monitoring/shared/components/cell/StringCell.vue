<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed } from 'vue'

import BaseCell, { type CellLink } from './BaseCell.vue'

const props = withDefaults(
  defineProps<{
    value: string | undefined
    hardBreakEvery?: number
    linkedTo?: CellLink | undefined
    columnId?: string | undefined
    emptyLabel?: string | undefined
  }>(),
  { hardBreakEvery: 15, linkedTo: undefined }
)

const SOFT_BREAK_CHARS = /([ \-_.])/g
const ZWSP = '​'

const display = computed(() => {
  const value = props.value ?? props.emptyLabel ?? 'n/a'
  const hardBreak = new RegExp(`([^\\s\\-_.]{${props.hardBreakEvery}})`, 'g')
  return value.replace(SOFT_BREAK_CHARS, `$1${ZWSP}`).replace(hardBreak, `$1${ZWSP}`)
})
</script>

<template>
  <BaseCell class="monitoring-string-cell" :column-id="columnId" :linked-to="linkedTo">
    <template #default>
      <span
        :title="value"
        class="monitoring-string-cell__text"
        :class="{
          'monitoring-string-cell__text--empty-string': display === 'n/a' || display === emptyLabel
        }"
      >
        {{ display }}
      </span>
    </template>
  </BaseCell>
</template>

<style scoped>
.monitoring-string-cell__text {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
  overflow: hidden;
  overflow-wrap: normal;
  word-break: normal;

  &.monitoring-string-cell__text--empty-string {
    font-style: italic;
    color: var(--font-color-dimmed);
  }
}

/* stylelint-disable selector-pseudo-class-no-unknown */
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.monitoring-string-cell :deep(.monitoring-base-cell__highlight) {
  flex: 1 1 auto;
  min-width: 0;
}
</style>
