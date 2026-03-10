<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { unref } from 'vue'

import DisabledTooltipWrapper from '@/dashboard/components/WidgetWorkflow/DisabledTooltipWrapper.vue'

import AvailableWidget from './AvailableWidget.vue'
import type { WidgetItemList } from './types'

interface AvailableWidgetsProps {
  availableItems: WidgetItemList
  enabledWidgets: string[]
  compact?: boolean
}

interface AvailableWidgetsEmits {
  (e: 'selectWidget', itemId: string): void
}

const props = defineProps<AvailableWidgetsProps>()
const emit = defineEmits<AvailableWidgetsEmits>()
const selectedWidget = defineModel<string | null>('selectedWidget', { default: null })
</script>

<template>
  <div
    class="db-available-widgets__container"
    :class="{ 'db-available-widgets__container-compact': props.compact }"
  >
    <div
      v-for="(item, index) in availableItems"
      :key="index"
      role="button"
      tabindex="0"
      :aria-label="unref(item.label)"
      class="db-available-widgets__item"
      @click="
        () => {
          if (enabledWidgets.includes(item.id)) {
            selectedWidget = item.id
            emit('selectWidget', item.id)
          }
        }
      "
    >
      <DisabledTooltipWrapper :disabled="!enabledWidgets.includes(item.id)">
        <AvailableWidget
          :label="item.label"
          :icon="item.icon"
          :disabled="!enabledWidgets.includes(item.id)"
          :selected="item.id === selectedWidget"
          :compact="props.compact"
        />
      </DisabledTooltipWrapper>
    </div>
  </div>
</template>

<style scoped>
.db-available-widgets__container {
  display: flex;
  flex-direction: row;
  gap: var(--dimension-4);
  width: 100%;
}

.db-available-widgets__item {
  min-width: 90px;
}

.db-available-widgets__container-compact {
  display: grid;
  grid-template-columns: none;
  grid-auto-flow: column;
  grid-auto-columns: 1fr;
  width: max-content;
}

.db-available-widgets__container-compact .db-available-widgets__item {
  min-width: 0;
}
</style>
