<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import CmkCatalogPanel from '@/components/CmkCatalogPanel.vue'
import CmkDropdown from '@/components/CmkDropdown'
import CmkIndent from '@/components/CmkIndent.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'

import DashboardPreviewContent from '@/dashboard/components/DashboardPreviewContent.vue'
import GraphTimeRange from '@/dashboard/components/TimeRange/GraphTimeRange.vue'
import ContentSpacer from '@/dashboard/components/Wizard/components/ContentSpacer.vue'
import RadioButton from '@/dashboard/components/Wizard/components/RadioButton.vue'
import FieldComponent from '@/dashboard/components/Wizard/components/TableForm/FieldComponent.vue'
import FieldDescription from '@/dashboard/components/Wizard/components/TableForm/FieldDescription.vue'
import TableForm from '@/dashboard/components/Wizard/components/TableForm/TableForm.vue'
import TableFormRow from '@/dashboard/components/Wizard/components/TableForm/TableFormRow.vue'
import SelectableWidgets from '@/dashboard/components/Wizard/components/WidgetSelection/SelectableWidgets.vue'
import WidgetVisualization from '@/dashboard/components/Wizard/components/WidgetVisualization/WidgetVisualization.vue'
import type { BaseWidgetProp } from '@/dashboard/components/Wizard/types'

import {
  VisualizationTimelineType,
  getVisualizationTypes
} from '../../composables/useSelectGraphTypes.ts'
import type { UseNotificationTimeline } from './composables/useNotificationTimeline'

const { _t } = usei18n()
defineProps<BaseWidgetProp>()
const handler = defineModel<UseNotificationTimeline>('handler', { required: true })

const widgetProps = computed(() => handler.value.widgetProps)

const availableVisualizationTypes = getVisualizationTypes()
</script>

<template>
  <CmkHeading type="h3">{{ _t('Choose a visualization type.') }}</CmkHeading>
  <ContentSpacer />
  <SelectableWidgets
    v-model:selected-widget="handler.visualizationType.value"
    :available-items="availableVisualizationTypes"
    :enabled-widgets="Object.values(VisualizationTimelineType)"
  />
  <ContentSpacer />
  <div v-if="!handler.isUpdating.value">
    <DashboardPreviewContent
      widget_id="notification-timeline-preview"
      :dashboard-key="dashboardKey"
      :general_settings="widgetProps.value!.general_settings!"
      :content="widgetProps.value!.content!"
      :effective-title="widgetProps.value!.effectiveTitle"
      :effective_filter_context="widgetProps.value!.effective_filter_context!"
    />
  </div>
  <div v-else class="db-notification-timeline__size-preview">&nbsp;</div>

  <ContentSpacer />

  <CmkCatalogPanel :title="_t('Data settings')">
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
      <TableFormRow>
        <FieldDescription>{{ _t('Notifications') }}</FieldDescription>
        <FieldComponent>
          <CmkDropdown
            v-model:selected-option="handler.logtarget.value"
            :options="handler.logtargetOptions"
            :label="_t('Notifications')"
          />
        </FieldComponent>
      </TableFormRow>
    </TableForm>
  </CmkCatalogPanel>

  <ContentSpacer />

  <CmkCatalogPanel :title="_t('Widget settings')">
    <WidgetVisualization
      v-model:show-title="handler.showTitle.value"
      v-model:show-title-background="handler.showTitleBackground.value"
      v-model:show-widget-background="handler.showWidgetBackground.value"
      v-model:title="handler.title.value"
      v-model:title-url="handler.titleUrl.value"
      v-model:title-url-enabled="handler.titleUrlEnabled.value"
      v-model:title-url-validation-errors="handler.titleUrlValidationErrors.value"
    />
  </CmkCatalogPanel>

  <ContentSpacer />
</template>
<style scoped>
.db-notification-timeline__size-preview {
  display: flex;
  flex-direction: column;
  position: relative;
  height: 240px;
  margin: 0;
  padding: var(--dimension-3);
  box-sizing: border-box;
  pointer-events: none;
  background-color: var(--db-content-bg-color);
}
</style>
