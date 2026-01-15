<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref, toValue } from 'vue'

import usei18n from '@/lib/i18n'

import DashboardPreviewContent from '@/dashboard/components/DashboardPreviewContent.vue'
import ContentSpacer from '@/dashboard/components/Wizard/components/ContentSpacer.vue'
import WidgetVisualization from '@/dashboard/components/Wizard/components/WidgetVisualization/WidgetVisualization.vue'
import { useWidgetVisualizationProps } from '@/dashboard/components/Wizard/components/WidgetVisualization/useWidgetVisualization.ts'
import CollapsibleContent from '@/dashboard/components/Wizard/components/collapsible/CollapsibleContent.vue'
import CollapsibleTitle from '@/dashboard/components/Wizard/components/collapsible/CollapsibleTitle.vue'
import type { EventStatsContent } from '@/dashboard/components/Wizard/types'
import type { ConfiguredFilters } from '@/dashboard/components/filter/types'
import { useDebounceRef } from '@/dashboard/composables/useDebounce.ts'
import { usePreviewWidgetTitle } from '@/dashboard/composables/useWidgetTitles'
import type { DashboardConstants, DashboardKey } from '@/dashboard/types/dashboard'
import type { WidgetContent, WidgetGeneralSettings, WidgetSpec } from '@/dashboard/types/widget'
import { buildWidgetEffectiveFilterContext } from '@/dashboard/utils.ts'

import Stage2Header from '../../../components/Stage2Header.vue'

const { _t } = usei18n()

interface Stage2Props {
  dashboardKey: DashboardKey
  filters: ConfiguredFilters
  dashboardConstants: DashboardConstants
  editWidgetSpec?: WidgetSpec | null
}

const props = defineProps<Stage2Props>()
const emit = defineEmits<{
  goPrev: []
  addWidget: [
    content: WidgetContent,
    generalSettings: WidgetGeneralSettings,
    filterUsesInfos: string[]
  ]
}>()

const displayVisualizationSettings = ref<boolean>(true)
const filterUsesInfos = ['host', 'event']

const {
  title,
  showTitle,
  showTitleBackground,
  showWidgetBackground,
  titleUrlEnabled,
  titleUrl,
  titleUrlValidationErrors,
  validate: validateTitle,
  widgetGeneralSettings
} = useWidgetVisualizationProps('$DEFAULT_TITLE$', props.editWidgetSpec?.general_settings)

const content: EventStatsContent = { type: 'event_stats' }
const debouncedGeneralSettings = useDebounceRef(widgetGeneralSettings, 300)
const effectiveTitle = usePreviewWidgetTitle(
  computed(() => {
    return {
      generalSettings: widgetGeneralSettings.value,
      content,
      effectiveFilters: props.filters
    }
  })
)

const widgetProps = computed(() => {
  return {
    general_settings: debouncedGeneralSettings.value,
    content,
    effectiveTitle: effectiveTitle.value,
    effective_filter_context: buildWidgetEffectiveFilterContext(
      content,
      props.filters,
      filterUsesInfos,
      props.dashboardConstants
    )
  }
})

const gotoNextStage = () => {
  const isValid = validateTitle()
  if (!isValid) {
    return
  }

  emit('addWidget', toValue(content), toValue(widgetGeneralSettings), filterUsesInfos)
}
</script>

<template>
  <Stage2Header :edit="!!editWidgetSpec" @back="emit('goPrev')" @save="gotoNextStage" />

  <DashboardPreviewContent
    widget_id="event-stats-preview"
    :dashboard-key="dashboardKey"
    :general_settings="widgetProps.general_settings"
    :content="widgetProps.content"
    :effective-title="widgetProps.effectiveTitle"
    :effective_filter_context="widgetProps.effective_filter_context"
  />

  <ContentSpacer />

  <CollapsibleTitle
    :title="_t('Widget settings')"
    :open="displayVisualizationSettings"
    @toggle-open="displayVisualizationSettings = !displayVisualizationSettings"
  />
  <CollapsibleContent :open="displayVisualizationSettings">
    <WidgetVisualization
      v-model:show-title="showTitle"
      v-model:show-title-background="showTitleBackground"
      v-model:show-widget-background="showWidgetBackground"
      v-model:title="title"
      v-model:title-url="titleUrl"
      v-model:title-url-enabled="titleUrlEnabled"
      v-model:title-url-validation-errors="titleUrlValidationErrors"
    />
  </CollapsibleContent>

  <ContentSpacer />
</template>
