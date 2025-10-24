<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref, toValue, watch } from 'vue'

import usei18n from '@/lib/i18n'

import CmkHeading from '@/components/typography/CmkHeading.vue'

import DashboardPreviewContent from '@/dashboard-wip/components/DashboardPreviewContent.vue'
import ActionBar from '@/dashboard-wip/components/Wizard/components/ActionBar.vue'
import ActionButton from '@/dashboard-wip/components/Wizard/components/ActionButton.vue'
import ContentSpacer from '@/dashboard-wip/components/Wizard/components/ContentSpacer.vue'
import WidgetVisualization from '@/dashboard-wip/components/Wizard/components/WidgetVisualization/WidgetVisualization.vue'
import { useWidgetVisualizationProps } from '@/dashboard-wip/components/Wizard/components/WidgetVisualization/useWidgetVisualization.ts'
import CollapsibleContent from '@/dashboard-wip/components/Wizard/components/collapsible/CollapsibleContent.vue'
import CollapsibleTitle from '@/dashboard-wip/components/Wizard/components/collapsible/CollapsibleTitle.vue'
import type { EventStatsContent, WidgetProps } from '@/dashboard-wip/components/Wizard/types'
import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'
import { useDebounceFn } from '@/dashboard-wip/composables/useDebounce.ts'
import type { DashboardConstants } from '@/dashboard-wip/types/dashboard'
import type { WidgetContent, WidgetGeneralSettings, WidgetSpec } from '@/dashboard-wip/types/widget'
import { buildWidgetEffectiveFilterContext } from '@/dashboard-wip/utils.ts'

const { _t } = usei18n()

interface Stage2Props {
  dashboardName: string
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
const configuredWidgetProps = ref<WidgetProps>()
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
} = useWidgetVisualizationProps('', props.editWidgetSpec?.general_settings)

const buildWidgetSpec = (): WidgetProps => {
  const content: EventStatsContent = { type: 'event_stats' }
  return {
    general_settings: widgetGeneralSettings.value,
    content,
    effective_filter_context: buildWidgetEffectiveFilterContext(
      content,
      props.filters,
      filterUsesInfos,
      props.dashboardConstants
    )
  }
}

const _updateWidgetProps = () => {
  configuredWidgetProps.value = buildWidgetSpec()
}

void _updateWidgetProps()

watch(
  [widgetGeneralSettings],
  useDebounceFn(() => {
    void _updateWidgetProps()
  }, 300),
  { deep: true }
)

const gotoNextStage = () => {
  const isValid = validateTitle()
  if (!isValid) {
    return
  }

  emit(
    'addWidget',
    toValue(configuredWidgetProps.value!.content),
    toValue(configuredWidgetProps.value!.general_settings),
    filterUsesInfos
  )
}

const widgetProps = computed(() => configuredWidgetProps)
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
      :action="() => emit('goPrev')"
      variant="secondary"
    />
    <ActionButton
      :label="editWidgetSpec ? _t('Save widget') : _t('Add & place widget')"
      :action="gotoNextStage"
      variant="primary"
    />
  </ActionBar>

  <ContentSpacer />

  <DashboardPreviewContent
    widget_id="event-stats-preview"
    :dashboard-name="dashboardName"
    :general_settings="widgetProps.value!.general_settings!"
    :content="widgetProps.value!.content!"
    :effective_filter_context="widgetProps.value!.effective_filter_context!"
  />

  <ContentSpacer />

  <CollapsibleTitle
    :title="_t('Widget visualization')"
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
