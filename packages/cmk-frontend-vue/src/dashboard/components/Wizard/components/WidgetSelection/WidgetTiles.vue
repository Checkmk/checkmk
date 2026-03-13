<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { unref } from 'vue'

import DisabledTooltipWrapper from '@/dashboard/components/WidgetWorkflow/DisabledTooltipWrapper.vue'

import WidgetTile from './WidgetTile.vue'
import type { WidgetItemList } from './types'

interface WidgetTilesProps {
  availableItems: WidgetItemList
  enabledWidgets: string[]
  compact?: boolean
}

interface WidgetTilesEmits {
  (e: 'selectWidget', itemId: string): void
}

const props = defineProps<WidgetTilesProps>()
const emit = defineEmits<WidgetTilesEmits>()
const selectedWidget = defineModel<string | null>('selectedWidget', { default: null })
</script>

<template>
  <div
    class="db-widget-tiles__container"
    :class="{ 'db-widget-tiles__container-compact': props.compact }"
  >
    <div
      v-for="(item, index) in availableItems"
      :key="index"
      role="button"
      tabindex="0"
      :aria-label="unref(item.label)"
      class="db-widget-tiles__item"
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
        <WidgetTile
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
.db-widget-tiles__container {
  display: flex;
  flex-direction: row;
  gap: var(--dimension-4);
  width: 100%;
}

.db-widget-tiles__item {
  flex: 1 1 0%;
}

.db-widget-tiles__container-compact {
  display: grid;
  grid-template-columns: none;
  grid-auto-flow: column;
  grid-auto-columns: 1fr;
  width: max-content;
}

.db-widget-tiles__container-compact .db-widget-tiles__item {
  min-width: 0;
}
</style>
