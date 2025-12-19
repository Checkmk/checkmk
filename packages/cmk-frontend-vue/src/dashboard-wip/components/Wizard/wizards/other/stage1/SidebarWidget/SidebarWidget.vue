<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import usei18n from '@/lib/i18n'

import DashboardPreviewContent from '@/dashboard-wip/components/DashboardPreviewContent.vue'
import ContentSpacer from '@/dashboard-wip/components/Wizard/components/ContentSpacer.vue'
import WidgetVisualization from '@/dashboard-wip/components/Wizard/components/WidgetVisualization/WidgetVisualization.vue'
import CollapsibleContent from '@/dashboard-wip/components/Wizard/components/collapsible/CollapsibleContent.vue'
import CollapsibleTitle from '@/dashboard-wip/components/Wizard/components/collapsible/CollapsibleTitle.vue'
import type { BaseWidgetProp, WidgetProps } from '@/dashboard-wip/components/Wizard/types'
import type { GetValidWidgetProps } from '@/dashboard-wip/components/Wizard/wizards/other/types'
import type { DashboardConstants } from '@/dashboard-wip/types/dashboard'
import type { WidgetSpec } from '@/dashboard-wip/types/widget'

import DataSelectionContainer from '../DataSelectionContainer.vue'
import SidebarElementSelector from './SidebarElementSelector.vue'
import { useSidebarElements } from './composables/useSidebarElements'
import { useSidebarWidget } from './composables/useSidebarWidget'

const { _t } = usei18n()
interface Props extends BaseWidgetProp {
  dashboardConstants: DashboardConstants
  editWidgetSpec: WidgetSpec | null
}
const props = defineProps<Props>()
const sidebarElements = useSidebarElements()
const handler = useSidebarWidget(
  sidebarElements.elements,
  props.dashboardConstants,
  props.editWidgetSpec
)

const displayVisualizationSettings = ref<boolean>(true)

function getValidWidgetProps(): WidgetProps | null {
  const validSidebarElement = sidebarElements.elements.value.some(
    (el) => el.id === handler.sidebarElementName.value
  )
  if (validSidebarElement && handler.validate()) {
    return handler.widgetProps.value
  }
  return null
}
defineExpose<GetValidWidgetProps>({ getValidWidgetProps })
</script>

<template>
  <div>
    <DataSelectionContainer>
      <SidebarElementSelector
        v-model:selected-sidebar-element="handler.sidebarElementName.value"
        :elements="sidebarElements.elements.value"
        :is-loading="sidebarElements.isLoading.value"
        :has-error="sidebarElements.hasError.value"
      />
    </DataSelectionContainer>

    <ContentSpacer />

    <DashboardPreviewContent
      widget_id="sidebar-element-preview"
      :dashboard-key="dashboardKey"
      :general_settings="handler.widgetProps.value.general_settings!"
      :content="handler.widgetProps.value.content!"
      :effective_filter_context="handler.widgetProps.value.effective_filter_context!"
    />

    <ContentSpacer />

    <CollapsibleTitle
      :title="_t('Widget settings')"
      :open="displayVisualizationSettings"
      @toggle-open="displayVisualizationSettings = !displayVisualizationSettings"
    />
    <CollapsibleContent :open="displayVisualizationSettings">
      <WidgetVisualization
        v-model:show-title="handler.showTitle.value"
        v-model:show-title-background="handler.showTitleBackground.value"
        v-model:show-widget-background="handler.showWidgetBackground.value"
        v-model:title="handler.title.value"
        v-model:title-url="handler.titleUrl.value"
        v-model:title-url-enabled="handler.titleUrlEnabled.value"
        v-model:title-url-validation-errors="handler.titleUrlValidationErrors.value"
      />
    </CollapsibleContent>

    <ContentSpacer />
  </div>
</template>
