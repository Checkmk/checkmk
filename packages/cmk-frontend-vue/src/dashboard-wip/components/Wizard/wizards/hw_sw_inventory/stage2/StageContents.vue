<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import DashboardPreviewContent from '@/dashboard-wip/components/DashboardPreviewContent.vue'
import type { WidgetProps } from '@/dashboard-wip/components/Wizard/types'
import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'
import type { DashboardConstants } from '@/dashboard-wip/types/dashboard'
import type { WidgetContent, WidgetGeneralSettings } from '@/dashboard-wip/types/widget'

import ContentSpacer from '../../../components/ContentSpacer.vue'
import Stage2Header from '../../../components/Stage2Header.vue'
import InventoryWidget from './InventoryWidget/InventoryWidget.vue'
import { useInventory } from './InventoryWidget/useInventory'

interface Stage2Props {
  filters: ConfiguredFilters
  widgetFilters: ConfiguredFilters
  dashboardName: string
  dashboardConstants: DashboardConstants
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

    emit('addWidget', content, generalSettings, props.widgetFilters)
  }
}

const gotoPrevStage = () => {
  emit('goPrev')
}

// Pass the editWidget prop to the composable for state hydration
const inventoryHandler = await useInventory(
  props.filters,
  props.dashboardConstants,
  props.editWidget
)
</script>

<template>
  <Stage2Header :edit="!!editWidget" @back="gotoPrevStage" @save="gotoNextStage" />

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
