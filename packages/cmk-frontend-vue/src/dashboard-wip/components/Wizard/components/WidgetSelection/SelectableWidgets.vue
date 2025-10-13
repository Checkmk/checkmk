<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import SelectableWidget from './SelectableWidget.vue'
import type { WidgetItemList } from './types'

interface SelectableWidgetsProps {
  availableItems: WidgetItemList
  enabledWidgets: string[]
}

defineProps<SelectableWidgetsProps>()
const selectedWidget = defineModel<string>('selectedWidget', { required: true })
</script>

<template>
  <div class="db-selectable-widgets__container">
    <div v-for="(item, index) in availableItems" :key="index">
      <SelectableWidget
        :id="item.id"
        :label="item.label"
        :icon="item.icon"
        :disabled="!enabledWidgets.includes(item.id)"
        :selected="item.id === selectedWidget"
        @click="(name) => (selectedWidget = name)"
      />
    </div>
  </div>
</template>

<style scoped>
.db-selectable-widgets__container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(0, 1fr));
  gap: 1rem;
  width: 100%;
}
</style>
