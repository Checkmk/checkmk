<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref, toValue } from 'vue'

import usei18n from '@/lib/i18n'

import CmkCollapsible from '@/components/CmkCollapsible.vue'
import CmkCollapsibleTitle from '@/components/CmkCollapsibleTitle.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'

import type { ContentProps } from '@/dashboard-wip/components/DashboardContent/types'
import DashboardPreviewContent from '@/dashboard-wip/components/DashboardPreviewContent.vue'
import ActionBar from '@/dashboard-wip/components/Wizard/components/ActionBar.vue'
import ActionButton from '@/dashboard-wip/components/Wizard/components/ActionButton.vue'
import ContentSpacer from '@/dashboard-wip/components/Wizard/components/ContentSpacer.vue'
import WidgetVisualization from '@/dashboard-wip/components/Wizard/components/WidgetVisualization/WidgetVisualization.vue'
import type { UseWidgetVisualizationProps } from '@/dashboard-wip/components/Wizard/components/WidgetVisualization/useWidgetVisualization'
import type {
  EffectiveWidgetFilterContext,
  EmbeddedViewContent,
  LinkedViewContent,
  WidgetGeneralSettings
} from '@/dashboard-wip/types/widget'

const { _t } = usei18n()

interface Stage3Props {
  dashboardName: string

  widget_id: string
  content: EmbeddedViewContent | LinkedViewContent
  effective_filter_context: EffectiveWidgetFilterContext
}

const props = defineProps<Stage3Props>()
const emit = defineEmits<{
  goPrev: []
  addWidget: [generalSettings: WidgetGeneralSettings]
}>()

const visualizationProps = defineModel<UseWidgetVisualizationProps>('visualization', {
  required: true
})

const generalSettings = computed<WidgetGeneralSettings>(() => ({
  title: visualizationProps.value.generateTitleSpec(),
  render_background: toValue(visualizationProps.value.showWidgetBackground)
}))

const widgetContentProps = computed<ContentProps>(
  () =>
    ({
      widget_id: props.widget_id,
      content: props.content,
      effective_filter_context: props.effective_filter_context,
      dashboardName: props.dashboardName,
      general_settings: generalSettings.value
    }) as ContentProps
)

function saveWidget() {
  const isValid = visualizationProps.value.validate()
  if (isValid) {
    emit('addWidget', toValue(generalSettings))
  }
}

const displayVisualizationSettings = ref<boolean>(true)
</script>

<template>
  <CmkHeading type="h1">
    {{ _t('Visualization') }}
  </CmkHeading>

  <ContentSpacer />

  <ActionBar align-items="left">
    <ActionButton
      :label="_t('Previous step')"
      :icon="{ name: 'back', side: 'left' }"
      :action="() => $emit('goPrev')"
      variant="secondary"
    />
    <ActionButton :label="_t('Add & place widget')" :action="saveWidget" variant="secondary" />
  </ActionBar>

  <ContentSpacer />

  <DashboardPreviewContent v-bind="widgetContentProps" />

  <ContentSpacer />

  <CmkCollapsibleTitle
    :title="_t('Widget visualization')"
    :open="displayVisualizationSettings"
    class="collapsible"
    @toggle-open="displayVisualizationSettings = !displayVisualizationSettings"
  />
  <CmkCollapsible :open="displayVisualizationSettings">
    <WidgetVisualization
      v-model:show-title="visualizationProps.showTitle.value"
      v-model:show-title-background="visualizationProps.showTitleBackground.value"
      v-model:show-widget-background="visualizationProps.showWidgetBackground.value"
      v-model:title="visualizationProps.title.value"
      v-model:title-url="visualizationProps.titleUrl.value"
      v-model:title-url-enabled="visualizationProps.titleUrlEnabled.value"
      v-model:title-url-validation-errors="visualizationProps.titleUrlValidationErrors.value"
    />
  </CmkCollapsible>
</template>
