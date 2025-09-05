<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { WorkflowItem } from '../WidgetWorkflowTypes'
import WorkflowCard from './WorkflowCard.vue'

export interface AddWidgetDialogProperties {
  workflowItems: Record<string, WorkflowItem>
}

const props = defineProps<AddWidgetDialogProperties>()

const emit = defineEmits(['select'])
</script>

<template>
  <div class="add-widget-page__wrapper">
    <div class="add-widget-page__grid-container">
      <WorkflowCard
        v-for="(item, id) in props.workflowItems"
        :key="id"
        :title="item.title"
        :icon="item.icon"
        :subtitle="item.subtitle"
        :icon_emblem="item.icon_emblem"
        @select="emit('select', id)"
      />
    </div>
  </div>
</template>

<style scoped>
.add-widget-page__wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  height: 100%;
  padding: var(--spacing-double);
  box-sizing: border-box;
}

.add-widget-page__grid-container {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  grid-gap: var(--spacing-double);
  padding: var(--spacing-double);
  width: 100%;
}

@media (max-width: 800px) {
  .add-widget-page__grid-container {
    grid-template-columns: 1fr;
  }
}
</style>
