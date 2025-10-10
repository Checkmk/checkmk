<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkIndent from '@/components/CmkIndent.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'

import DashboardPreviewContent from '@/dashboard-wip/components/DashboardPreviewContent.vue'
import GraphTimeRange from '@/dashboard-wip/components/TimeRange/GraphTimeRange.vue'
import ContentSpacer from '@/dashboard-wip/components/Wizard/components/ContentSpacer.vue'
import RadioButton from '@/dashboard-wip/components/Wizard/components/RadioButton.vue'
import FieldComponent from '@/dashboard-wip/components/Wizard/components/TableForm/FieldComponent.vue'
import FieldDescription from '@/dashboard-wip/components/Wizard/components/TableForm/FieldDescription.vue'
import TableForm from '@/dashboard-wip/components/Wizard/components/TableForm/TableForm.vue'
import TableFormRow from '@/dashboard-wip/components/Wizard/components/TableForm/TableFormRow.vue'
import WidgetVisualization from '@/dashboard-wip/components/Wizard/components/WidgetVisualization/WidgetVisualization.vue'
import CollapsibleContent from '@/dashboard-wip/components/Wizard/components/collapsible/CollapsibleContent.vue'
import CollapsibleTitle from '@/dashboard-wip/components/Wizard/components/collapsible/CollapsibleTitle.vue'
import type { BaseWidgetProp } from '@/dashboard-wip/components/Wizard/types'

import SelectableWidgets from '../../../../components/WidgetSelection/SelectableWidgets.vue'
import {
  VisualizationTimelineType,
  getVisualizationTypes
} from '../../composables/useSelectGraphTypes.ts'
import type { UseAlertTimeline } from './composables/useAlertTimeline'

const { _t } = usei18n()
defineProps<BaseWidgetProp>()
const handler = defineModel<UseAlertTimeline>('handler', { required: true })

const displayDataSettings = ref<boolean>(true)
const displayVisualizationSettings = ref<boolean>(true)
const widgetProps = computed(() => handler.value.widgetProps)

const selectedVisualizationType = ref<VisualizationTimelineType>(VisualizationTimelineType.BARPLOT)
const availableVisualizationTypes = getVisualizationTypes()
</script>

<template>
  <CmkHeading type="h3">{{ _t('Choose a visualization type.') }}</CmkHeading>

  <SelectableWidgets
    v-model:selected-widget="selectedVisualizationType"
    :available-items="availableVisualizationTypes"
    :enabled-widgets="Object.keys(VisualizationTimelineType)"
  />

  <DashboardPreviewContent
    widget_id="alert-overview-preview"
    :dashboard-name="dashboardName"
    :general_settings="widgetProps.value!.general_settings!"
    :content="widgetProps.value!.content!"
    :effective_filter_context="widgetProps.value!.effective_filter_context!"
  />

  <ContentSpacer />

  <CollapsibleTitle
    :title="_t('Data settings')"
    :open="displayDataSettings"
    class="collapsible"
    @toggle-open="displayDataSettings = !displayDataSettings"
  />
  <CollapsibleContent :open="displayDataSettings">
    <TableForm>
      <TableFormRow>
        <FieldDescription>{{ _t('Time range') }}</FieldDescription>
        <FieldComponent>
          <GraphTimeRange v-model:selected-timerange="handler.timeRange.value" />
        </FieldComponent>
      </TableFormRow>
      <TableFormRow>
        <FieldDescription>{{ _t('Time resolution') }}</FieldDescription>
        <FieldComponent>
          <div class="db-alert-timeline__item">
            <CmkIndent>
              <div class="db-alert-timeline__item">
                <RadioButton
                  v-model="handler.timeResolution.value"
                  name="resolution"
                  value="hour"
                  :label="_t('Show per hour')"
                />
              </div>

              <div class="db-alert-timeline__item">
                <RadioButton
                  v-model="handler.timeResolution.value"
                  name="resolution"
                  value="day"
                  :label="_t('Show per day')"
                />
              </div>
            </CmkIndent>
          </div>
        </FieldComponent>
      </TableFormRow>
    </TableForm>
  </CollapsibleContent>

  <ContentSpacer />

  <CollapsibleTitle
    :title="_t('Widget settings')"
    :open="displayVisualizationSettings"
    class="collapsible"
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
</template>
