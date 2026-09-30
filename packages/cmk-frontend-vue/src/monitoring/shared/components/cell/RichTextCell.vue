<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed, useSlots } from 'vue'

import BaseCell, { type CellLink, type CellVerticalAlign } from './BaseCell.vue'

const props = withDefaults(
  defineProps<{
    value?: string | undefined
    linkedTo?: CellLink | undefined
    columnId?: string | undefined
    emptyLabel?: string | undefined
    button?: boolean | undefined
    verticalAlign?: CellVerticalAlign | undefined
    noWrap?: boolean | undefined
    title?: string | undefined
  }>(),
  { value: undefined, linkedTo: undefined }
)

const emit = defineEmits<{
  (event: 'click', payload: MouseEvent): void
}>()

const slots = useSlots()

const display = computed(() => props.value ?? props.emptyLabel ?? 'n/a')

const isEmpty = computed(
  () => slots.default === undefined && (props.value === undefined || props.value === '')
)
</script>

<template>
  <BaseCell
    class="monitoring-rich-text-cell"
    :column-id="columnId"
    :linked-to="linkedTo"
    :button="button"
    :vertical-align="verticalAlign"
    :no-wrap="noWrap"
    @click="emit('click', $event)"
  >
    <template #default>
      <div
        :title="title ?? value"
        class="monitoring-rich-text-cell__content"
        :class="{ 'monitoring-rich-text-cell__content--empty': isEmpty }"
      >
        <slot>{{ display }}</slot>
      </div>
    </template>
  </BaseCell>
</template>

<style scoped>
.monitoring-rich-text-cell__content {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
  overflow: hidden;
  overflow-wrap: anywhere;

  &.monitoring-rich-text-cell__content--empty {
    font-style: italic;
    color: var(--font-color-dimmed);
  }
}

/* stylelint-disable selector-pseudo-class-no-unknown */
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.monitoring-rich-text-cell :deep(.monitoring-base-cell__highlight) {
  flex: 1 1 auto;
  min-width: 0;
}
</style>
