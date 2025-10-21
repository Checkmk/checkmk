<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkHeading from '@/components/typography/CmkHeading.vue'

import DashboardPreviewContent from '@/dashboard-wip/components/DashboardPreviewContent.vue'
import type { WidgetProps } from '@/dashboard-wip/components/Wizard/types'
import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'
import type { WidgetContent, WidgetGeneralSettings } from '@/dashboard-wip/types/widget'

import ActionBar from '../../../components/ActionBar.vue'
import ActionButton from '../../../components/ActionButton.vue'
import ContentSpacer from '../../../components/ContentSpacer.vue'
import InventoryWidget from './InventoryWidget/InventoryWidget.vue'
import { useInventory } from './InventoryWidget/useInventory'

const { _t } = usei18n()

interface Stage2Props {
  filters: ConfiguredFilters
  dashboardName: string
  editWidget: WidgetProps | null
}

const props = defineProps<Stage2Props>()

const emit = defineEmits<{
  goPrev: []
  addWidget: [
    content: WidgetContent,
    generalSettings: WidgetGeneralSettings,
    filters: ConfiguredFilters
  ]
}>()

const gotoNextStage = () => {
  if (!inventoryHandler) {
    return
  }

  const isValid = inventoryHandler?.validate()

  if (isValid) {
    const content: WidgetContent = inventoryHandler.widgetProps.value!.content
    const generalSettings: WidgetGeneralSettings =
      inventoryHandler.widgetProps.value!.general_settings

    emit('addWidget', content, generalSettings, props.filters)
  }
}

const gotoPrevStage = () => {
  emit('goPrev')
}

// Pass the editWidget prop to the composable for state hydration
const inventoryHandler = useInventory(props.filters, props.editWidget)
</script>

<template>
  <CmkHeading type="h1">
    {{ _t('Widget data') }}
  </CmkHeading>

  <ContentSpacer />

  <ActionBar align-items="left">
    <ActionButton
      :label="_t('Previous step')"
      :icon="{ name: 'back', side: 'left' }"
      :action="gotoPrevStage"
      variant="secondary"
    />
    <ActionButton :label="_t('Add & place widget')" :action="gotoNextStage" variant="primary" />
  </ActionBar>

  <ContentSpacer />

  <DashboardPreviewContent
    v-if="inventoryHandler.widgetProps.value"
    widget_id="inventory-preview"
    class="inventory-widget__preview"
    :dashboard-name="props.dashboardName"
    :general_settings="inventoryHandler.widgetProps.value.general_settings"
    :content="inventoryHandler.widgetProps.value.content"
    :effective_filter_context="inventoryHandler.widgetProps.value.effective_filter_context"
  />

  <ContentSpacer />

  <InventoryWidget v-model:handler="inventoryHandler" />
</template>
