<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, getCurrentInstance } from 'vue'

import AvailableWidget from './AvailableWidget.vue'
import type { WidgetItemList } from './types'

interface AvailableWidgetsProps {
  availableItems: WidgetItemList
  enabledWidgets: string[]
}

interface AvailableWidgetEmits {
  (e: 'selectWidget', itemId: string): void
}

defineProps<AvailableWidgetsProps>()
const emit = defineEmits<AvailableWidgetEmits>()

const isClickable = computed(() => !!getCurrentInstance()?.vnode.props?.onSelectWidget)

const handleClick = (itemId: string) => {
  if (isClickable.value) {
    emit('selectWidget', itemId)
  }
}
</script>

<template>
  <div class="db-available-widgets__container">
    <div
      v-for="(item, index) in availableItems"
      :key="index"
      class="db-available-widgets__item"
      @click="() => handleClick(item.id)"
    >
      <AvailableWidget
        :label="item.label"
        :icon="item.icon"
        :disabled="!enabledWidgets.includes(item.id)"
        :is-button="isClickable"
      />
    </div>
  </div>
</template>

<style scoped>
.db-available-widgets__container {
  display: flex;
  flex-direction: row;
  gap: var(--dimension-4);
  justify-content: space-between;
  width: 100%;
}

.db-available-widgets__item {
  flex: 1 1 0px;
}
</style>
