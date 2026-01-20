<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import AvailableWidget from './AvailableWidget.vue'
import type { WidgetItemList } from './types'

interface AvailableWidgetsProps {
  availableItems: WidgetItemList
  enabledWidgets: string[]
}

interface AvailableWidgetsEmits {
  (e: 'selectWidget', itemId: string): void
}

defineProps<AvailableWidgetsProps>()
const emit = defineEmits<AvailableWidgetsEmits>()
</script>

<template>
  <div class="db-available-widgets__container">
    <div
      v-for="(item, index) in availableItems"
      :key="index"
      role="button"
      :aria-label="item.label"
      class="db-available-widgets__item"
      @click="
        () => {
          if (enabledWidgets.includes(item.id)) {
            emit('selectWidget', item.id)
          }
        }
      "
    >
      <AvailableWidget
        :label="item.label"
        :icon="item.icon"
        :disabled="!enabledWidgets.includes(item.id)"
      />
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
</style>
