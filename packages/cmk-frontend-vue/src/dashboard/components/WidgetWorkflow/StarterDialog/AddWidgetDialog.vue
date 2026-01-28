<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkSlideIn from '@/components/CmkSlideIn.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'

import CloseButton from '@/dashboard/components/Wizard/components/CloseButton.vue'
import ContentSpacer from '@/dashboard/components/Wizard/components/ContentSpacer.vue'
import WizardStageContainer from '@/dashboard/components/Wizard/components/WizardStageContainer.vue'
import { DashboardFeatures } from '@/dashboard/types/dashboard'

import type { WorkflowItem } from '../WidgetWorkflowTypes'
import WorkflowListItem from './WorkflowListItem.vue'

const { _t } = usei18n()

export interface AddWidgetDialogProperties {
  workflowItems: Record<string, WorkflowItem>
  open: boolean
  availableFeatures: DashboardFeatures
}

const props = defineProps<AddWidgetDialogProperties>()

defineEmits(['close', 'select'])

const isDisabled = (id: string): boolean => {
  return (
    props.availableFeatures === DashboardFeatures.RESTRICTED &&
    ['custom_graphs', 'hw_sw_inventory', 'alerts_notifications'].includes(id)
  )
}
</script>

<template>
  <CmkSlideIn :open="props.open" :size="'small'" @close="$emit('close')">
    <WizardStageContainer>
      <CmkHeading type="h1">
        {{ _t('Add widget') }}
      </CmkHeading>
      <CloseButton @close="() => $emit('close')" />

      <ContentSpacer :dimension="8" />

      <div class="db-add-widget-dialog__container">
        <WorkflowListItem
          v-for="(item, id) in props.workflowItems"
          :key="id"
          :title="item.title"
          :icon="item.icon"
          :subtitle="item.subtitle"
          :icon_emblem="item.icon_emblem"
          :disabled="isDisabled(id)"
          @select="$emit('select', id)"
        />
      </div>
    </WizardStageContainer>
  </CmkSlideIn>
</template>

<style scoped>
.db-add-widget-dialog__container {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
}
</style>
