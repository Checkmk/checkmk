<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import PluginOutput from '../PluginOutput.vue'
import BaseCell, { type CellLink, type CellVerticalAlign } from './BaseCell.vue'
import { useSoftBreak } from './base/useSoftBreak'

const props = withDefaults(
  defineProps<{
    value: string | undefined
    hardBreakEvery?: number
    linkedTo?: CellLink | undefined
    columnId?: string | undefined
    emptyLabel?: string | undefined
    button?: boolean | undefined
    verticalAlign?: CellVerticalAlign | undefined
    noWrap?: boolean | undefined
    /** Renders the state markers a check embeds in its output, for a cell showing one. */
    stateMarkers?: boolean | undefined
  }>(),
  { hardBreakEvery: 15, linkedTo: undefined }
)

const emit = defineEmits<{
  (event: 'click', payload: MouseEvent): void
}>()

const display = useSoftBreak(
  () => props.value ?? props.emptyLabel ?? 'n/a',
  () => props.hardBreakEvery
)
</script>

<template>
  <BaseCell
    class="monitoring-string-cell"
    :column-id="columnId"
    :linked-to="linkedTo"
    :button="button"
    :vertical-align="verticalAlign"
    :no-wrap="noWrap"
    @click="emit('click', $event)"
  >
    <template #default>
      <span
        :title="value"
        class="monitoring-string-cell__text"
        :class="{
          'monitoring-string-cell__text--empty-string': display === 'n/a' || display === emptyLabel
        }"
      >
        <PluginOutput
          v-if="stateMarkers && value"
          :output="value"
          :hard-break-every="hardBreakEvery"
        />
        <template v-else>{{ display }}</template>
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

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.monitoring-string-cell :deep(.monitoring-base-cell__button) .monitoring-string-cell__text {
  width: auto;
  max-width: 100%;
}
</style>
