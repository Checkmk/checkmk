<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkSlideIn from 'cmk-ui-library/components/CmkSlideIn'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, nextTick } from 'vue'

import ContentSpacer from '@/dashboard/components/ContentSpacer.vue'
import CloseButton from '@/dashboard/components/Wizard/components/CloseButton.vue'
import StepsHeader from '@/dashboard/components/Wizard/components/StepsHeader.vue'
import WizardStageContainer from '@/dashboard/components/Wizard/components/WizardStageContainer.vue'
import { DashboardFeatures } from '@/dashboard/types/dashboard'

import {
  type WorkflowCatalog,
  type WorkflowGroup,
  type WorkflowItem,
  isWorkflowGroup
} from '../WidgetWorkflowTypes'
import WorkflowListItem from './WorkflowListItem.vue'

const { _t } = usei18n()

export interface AddWidgetDialogProperties {
  workflowItems: WorkflowCatalog
  open: boolean
  dashboardFeatures: DashboardFeatures
}

const props = defineProps<AddWidgetDialogProperties>()

const activeGroupKey = defineModel<string | null>('activeGroupKey', { required: true })

const emit = defineEmits<{
  select: [workflowKey: string]
  close: []
}>()

const requiresHigherEdition = (workflowKey: string): boolean => {
  return (
    props.dashboardFeatures === DashboardFeatures.RESTRICTED &&
    ['custom_graphs', 'hw_sw_inventory', 'alerts_notifications'].includes(workflowKey)
  )
}

const isAvailable = (workflowKey: string, workflow: WorkflowItem): boolean =>
  !requiresHigherEdition(workflowKey) && workflow.unavailableReason === undefined

const activeGroup = computed((): WorkflowGroup | null => {
  if (activeGroupKey.value === null) {
    return null
  }
  const workflow = props.workflowItems[activeGroupKey.value]
  return isWorkflowGroup(workflow) ? workflow : null
})

const visibleWorkflows = computed(
  (): Record<string, WorkflowItem> => activeGroup.value?.subWorkflows ?? props.workflowItems
)

type WorkflowRow = InstanceType<typeof WorkflowListItem>

const rowsByWorkflowKey = new Map<string, WorkflowRow>()

function registerRow(workflowKey: string, row: unknown) {
  if (row) {
    rowsByWorkflowKey.set(workflowKey, row as WorkflowRow)
  } else {
    rowsByWorkflowKey.delete(workflowKey)
  }
}

function focusRow(workflowKey: string) {
  rowsByWorkflowKey.get(workflowKey)?.focus()
}

function findFirstAvailableWorkflowKey(workflows: Record<string, WorkflowItem>): string | null {
  for (const [workflowKey, workflow] of Object.entries(workflows)) {
    if (isAvailable(workflowKey, workflow)) {
      return workflowKey
    }
  }
  return null
}

async function enterGroup(groupKey: string, group: WorkflowGroup) {
  activeGroupKey.value = groupKey
  await nextTick()
  const firstAvailableKey = findFirstAvailableWorkflowKey(group.subWorkflows)
  if (firstAvailableKey !== null) {
    focusRow(firstAvailableKey)
  }
}

async function leaveGroup() {
  const leftGroupKey = activeGroupKey.value
  activeGroupKey.value = null
  await nextTick()
  if (leftGroupKey !== null) {
    focusRow(leftGroupKey)
  }
}

function selectWorkflow(workflowKey: string, workflow: WorkflowItem) {
  if (isWorkflowGroup(workflow)) {
    void enterGroup(workflowKey, workflow)
    return
  }
  emit('select', workflowKey)
}
</script>

<template>
  <CmkSlideIn
    :open="props.open"
    :size="'small'"
    :aria-label="_t('Add widget')"
    @close="emit('close')"
  >
    <WizardStageContainer>
      <StepsHeader
        :title="activeGroup?.title ?? _t('Add widget')"
        :hide-back-button="activeGroup === null"
        @back="leaveGroup"
      />
      <CloseButton @close="() => emit('close')" />

      <ContentSpacer :dimension="8" />

      <div class="db-add-widget-dialog__container">
        <WorkflowListItem
          v-for="(workflow, workflowKey) in visibleWorkflows"
          :key="workflowKey"
          :ref="(row) => registerRow(workflowKey, row)"
          :title="workflow.title"
          :icon="workflow.icon"
          :subtitle="workflow.subtitle"
          :icon_emblem="workflow.icon_emblem"
          :unavailable-reason="workflow.unavailableReason"
          :requires-higher-edition="requiresHigherEdition(workflowKey)"
          @select="selectWorkflow(workflowKey, workflow)"
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
