<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import { DashboardFeatures } from '@/dashboard/types/dashboard'

import type { WorkflowItem } from '../WidgetWorkflowTypes'
import WorkflowCard from './WorkflowCard.vue'

export interface AddWidgetDialogProperties {
  workflowItems: Record<string, WorkflowItem>
  availableFeatures: DashboardFeatures
}

const { _t } = usei18n()

const props = defineProps<AddWidgetDialogProperties>()

const emit = defineEmits(['select'])

const isDisabled = (id: string): boolean => {
  return (
    props.availableFeatures === DashboardFeatures.RESTRICTED &&
    ['custom_graphs', 'hw_sw_inventory', 'alerts_notifications'].includes(id)
  )
}
</script>

<template>
  <div class="db-add-widget-page__wrapper" role="region" :aria-label="_t('Add widget')">
    <div class="db-add-widget-page__center-container">
      <div class="db-add-widget-page__grid-container">
        <WorkflowCard
          v-for="(item, id) in props.workflowItems"
          :key="id"
          :title="item.title"
          :icon="item.icon"
          :subtitle="item.subtitle"
          :icon_emblem="item.icon_emblem"
          :disabled="isDisabled(id)"
          @select="emit('select', id)"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.db-add-widget-page__wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  box-sizing: border-box;
  padding: var(--spacing-double);
}

.db-add-widget-page__center-container {
  margin: 0;
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
}

.db-add-widget-page__grid-container {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--dimension-4);
  padding: var(--spacing);
  width: 100%;
  max-width: 1000px;
  vertical-align: middle;
}

@media (width < 800px) {
  .db-add-widget-page__grid-container {
    grid-template-columns: 1fr;
  }
}
</style>
