<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, toValue } from 'vue'

import usei18n from '@/lib/i18n'

import CmkCatalogPanel from '@/components/CmkCatalogPanel.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'

import type { ContentProps } from '@/dashboard/components/DashboardContent/types'
import DashboardPreviewContent from '@/dashboard/components/DashboardPreviewContent.vue'
import ActionBar from '@/dashboard/components/Wizard/components/ActionBar.vue'
import ActionButton from '@/dashboard/components/Wizard/components/ActionButton.vue'
import ContentSpacer from '@/dashboard/components/Wizard/components/ContentSpacer.vue'
import WidgetVisualization from '@/dashboard/components/Wizard/components/WidgetVisualization/WidgetVisualization.vue'
import type { UseWidgetVisualizationProps } from '@/dashboard/components/Wizard/components/WidgetVisualization/useWidgetVisualization'
import { usePreviewWidgetTitle } from '@/dashboard/composables/useWidgetTitles'
import type { DashboardKey } from '@/dashboard/types/dashboard'
import type {
  EffectiveWidgetFilterContext,
  EmbeddedViewContent,
  LinkedViewContent,
  WidgetGeneralSettings
} from '@/dashboard/types/widget'

const { _t } = usei18n()

interface Stage3Props {
  dashboardKey: DashboardKey

  widget_id: string
  content: EmbeddedViewContent | LinkedViewContent
  effective_filter_context: EffectiveWidgetFilterContext
  isEditMode?: boolean
}

const props = defineProps<Stage3Props>()
const emit = defineEmits<{
  goPrev: []
  addWidget: [generalSettings: WidgetGeneralSettings]
}>()

const visualizationProps = defineModel<UseWidgetVisualizationProps>('visualization', {
  required: true
})

const effectiveTitle = usePreviewWidgetTitle(
  computed(() => {
    return {
      generalSettings: visualizationProps.value.widgetGeneralSettings.value,
      content: props.content,
      effectiveFilters: props.effective_filter_context.filters
    }
  })
)

const widgetContentProps = computed<ContentProps>(
  () =>
    ({
      widget_id: props.widget_id,
      content: props.content,
      effectiveTitle: effectiveTitle.value,
      effective_filter_context: props.effective_filter_context,
      dashboardKey: props.dashboardKey,
      general_settings: visualizationProps.value.widgetGeneralSettings.value
    }) as ContentProps
)

function saveWidget() {
  const isValid = visualizationProps.value.validate()
  if (isValid) {
    emit('addWidget', toValue(visualizationProps.value.widgetGeneralSettings))
  }
}
</script>

<template>
  <CmkHeading type="h1">
    {{ _t('Visualization') }}
  </CmkHeading>

  <ContentSpacer />

  <ActionBar align-items="left">
    <ActionButton
      :label="_t('Previous step')"
      :icon="{ name: 'continue', side: 'left', rotate: 180 }"
      :action="() => $emit('goPrev')"
      variant="secondary"
    />
    <ActionButton
      :label="!!isEditMode ? _t('Save widget') : _t('Add & place widget')"
      :action="saveWidget"
      variant="primary"
    />
  </ActionBar>
  <ContentSpacer :dimension="11" />

  <DashboardPreviewContent v-bind="widgetContentProps" />

  <ContentSpacer />

  <CmkCatalogPanel :title="_t('Widget settings')">
    <WidgetVisualization
      v-model:show-title="visualizationProps.showTitle.value"
      v-model:show-title-background="visualizationProps.showTitleBackground.value"
      v-model:show-widget-background="visualizationProps.showWidgetBackground.value"
      v-model:title="visualizationProps.title.value"
      v-model:title-url="visualizationProps.titleUrl.value"
      v-model:title-url-enabled="visualizationProps.titleUrlEnabled.value"
      v-model:title-url-validation-errors="visualizationProps.titleUrlValidationErrors.value"
    />
  </CmkCatalogPanel>
</template>
