<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkCatalogPanel from 'cmk-ui-library/components/CmkCatalogPanel.vue'
import type { DateTimeRange } from 'cmk-ui-library/components/date-time'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { randomId } from 'cmk-ui-library/lib/randomId'
import { computed } from 'vue'

import ContentSpacer from '@/dashboard/components/ContentSpacer.vue'
import type { ContentProps } from '@/dashboard/components/DashboardContent/types'
import DashboardPreviewContent from '@/dashboard/components/DashboardPreviewContent.vue'
import ActionBar from '@/dashboard/components/Wizard/components/ActionBar.vue'
import ActionButton from '@/dashboard/components/Wizard/components/ActionButton.vue'
import WidgetVisualization from '@/dashboard/components/Wizard/components/WidgetVisualization/WidgetVisualization.vue'
import type { UseWidgetVisualizationProps } from '@/dashboard/components/Wizard/components/WidgetVisualization/useWidgetVisualization'
import { MAX_WIZARD_FORM_WIDTH } from '@/dashboard/components/Wizard/constants'
import { usePreviewWidgetTitle } from '@/dashboard/composables/useWidgetTitles'
import type { DashboardKey } from '@/dashboard/types/dashboard'
import type {
  EffectiveWidgetFilterContext,
  MonitoringTableContent,
  WidgetGeneralSettings
} from '@/dashboard/types/widget'

const { _t } = usei18n()

const props = defineProps<{
  tick: number
  range: DateTimeRange
  dashboardKey: DashboardKey
  content: MonitoringTableContent
  effectiveFilterContext: EffectiveWidgetFilterContext
  isEditMode: boolean
}>()

const emit = defineEmits<{
  goPrev: []
  addWidget: [generalSettings: WidgetGeneralSettings]
}>()

const visualization = defineModel<UseWidgetVisualizationProps>('visualization', {
  required: true
})

const effectiveTitle = usePreviewWidgetTitle(
  computed(() => ({
    generalSettings: visualization.value.widgetGeneralSettings.value,
    content: props.content,
    effectiveFilters: props.effectiveFilterContext.filters
  }))
)

const previewId = randomId()

const previewProps = computed(
  () =>
    ({
      widget_id: previewId,
      content: props.content,
      effectiveTitle: effectiveTitle.value,
      effective_filter_context: props.effectiveFilterContext,
      dashboardKey: props.dashboardKey,
      tick: props.tick,
      range: props.range,
      general_settings: visualization.value.widgetGeneralSettings.value
    }) as ContentProps
)

function saveWidget() {
  if (visualization.value.validate()) {
    emit('addWidget', visualization.value.widgetGeneralSettings.value)
  }
}
</script>

<template>
  <CmkHeading type="h1">{{ _t('Visualization') }}</CmkHeading>

  <ContentSpacer />

  <ActionBar align-items="left">
    <ActionButton
      :label="_t('Previous step')"
      :icon="{ name: 'continue', side: 'left', rotate: 180 }"
      variant="secondary"
      :action="() => emit('goPrev')"
    />
    <ActionButton
      :label="isEditMode ? _t('Save widget') : _t('Add & place widget')"
      variant="primary"
      :action="saveWidget"
    />
  </ActionBar>

  <ContentSpacer :dimension="11" />

  <DashboardPreviewContent v-bind="previewProps" />

  <ContentSpacer />

  <CmkCatalogPanel :title="_t('Widget settings')" variant="padded">
    <div :style="`max-width: ${MAX_WIZARD_FORM_WIDTH}px`">
      <WidgetVisualization
        v-model:show-title="visualization.showTitle.value"
        v-model:show-title-background="visualization.showTitleBackground.value"
        v-model:show-widget-background="visualization.showWidgetBackground.value"
        v-model:title="visualization.title.value"
        v-model:title-url="visualization.titleUrl.value"
        v-model:title-url-enabled="visualization.titleUrlEnabled.value"
        v-model:title-url-validation-errors="visualization.titleUrlValidationErrors.value"
        :title-macros="visualization.titleMacros.value"
      />
    </div>
  </CmkCatalogPanel>
</template>
