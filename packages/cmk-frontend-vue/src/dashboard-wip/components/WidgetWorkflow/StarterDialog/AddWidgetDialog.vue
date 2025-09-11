<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkSlideInDialog from '@/components/CmkSlideInDialog.vue'

import type { WorkflowItem } from '../WidgetWorkflowTypes'
import WorkflowListItem from './WorkflowListItem.vue'

const { _t } = usei18n()

export interface AddWidgetDialogProperties {
  workflowItems: Record<string, WorkflowItem>
  open: boolean
}

const props = defineProps<AddWidgetDialogProperties>()

const emit = defineEmits(['close', 'select'])
</script>

<template>
  <CmkSlideInDialog
    :open="props.open"
    :header="{
      title: _t('Add widget'),
      closeButton: true
    }"
    @close="emit('close')"
  >
    <div class="add-widget-dialog__container">
      <WorkflowListItem
        v-for="(item, id) in props.workflowItems"
        :key="id"
        :title="item.title"
        :icon="item.icon"
        :subtitle="item.subtitle"
        :icon_emblem="item.icon_emblem"
        @select="emit('select', id)"
      />
    </div>
  </CmkSlideInDialog>
</template>

<style scoped>
.add-widget-dialog__container {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
  padding: var(--spacing-double);
}
</style>
