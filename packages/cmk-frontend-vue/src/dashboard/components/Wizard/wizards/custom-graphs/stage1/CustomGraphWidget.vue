<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import CmkCatalogPanel from '@/components/CmkCatalogPanel.vue'
import CmkInlineValidation from '@/components/user-input/CmkInlineValidation.vue'

import DashboardPreviewContent from '@/dashboard/components/DashboardPreviewContent.vue'
import GraphTimeRange from '@/dashboard/components/TimeRange/GraphTimeRange.vue'
import ContentSpacer from '@/dashboard/components/Wizard/components/ContentSpacer.vue'
import FieldComponent from '@/dashboard/components/Wizard/components/TableForm/FieldComponent.vue'
import FieldDescription from '@/dashboard/components/Wizard/components/TableForm/FieldDescription.vue'
import TableForm from '@/dashboard/components/Wizard/components/TableForm/TableForm.vue'
import TableFormRow from '@/dashboard/components/Wizard/components/TableForm/TableFormRow.vue'
import WidgetVisualization from '@/dashboard/components/Wizard/components/WidgetVisualization/WidgetVisualization.vue'
import type { BaseWidgetProp } from '@/dashboard/components/Wizard/types.ts'

import GraphRenderOptions from '../../../components/GraphRenderOptions/GraphRenderOptions.vue'
import AutocompleteCustomGraph from '../../../components/autocompleters/AutocompleteCustomGraph.vue'
import type { UseCustomGraph } from './composables/useCustomGraph.ts'

const { _t } = usei18n()

defineProps<BaseWidgetProp>()

const handler = defineModel<UseCustomGraph>('handler', { required: true })

const widgetProps = computed(() => handler.value.widgetProps)
</script>

<template>
  <div v-if="widgetProps.value === null" class="db-custom-graph-widget--preview-placeholder">
    <span>{{ _t('Select a custom graph') }}</span>
  </div>
  <DashboardPreviewContent
    v-else
    widget_id="graph-preview"
    :dashboard-key="dashboardKey"
    :general_settings="widgetProps.value!.general_settings!"
    :content="widgetProps.value!.content!"
    :effective-title="widgetProps.value!.effectiveTitle"
    :effective_filter_context="widgetProps.value!.effective_filter_context!"
  />
  <ContentSpacer />

  <CmkCatalogPanel :title="_t('Data settings')">
    <TableForm>
      <TableFormRow>
        <FieldDescription>{{ _t('Custom graph') }}</FieldDescription>
        <FieldComponent>
          <AutocompleteCustomGraph v-model:custom-graph="handler.customGraph.value" />
          <CmkInlineValidation
            v-if="handler.customGraphValidationErrors.value.length > 0"
            :validation="handler.customGraphValidationErrors.value"
          />
        </FieldComponent>
      </TableFormRow>

      <TableFormRow>
        <FieldDescription>{{ _t('Time range') }}</FieldDescription>
        <FieldComponent>
          <GraphTimeRange v-model:selected-timerange="handler.timeRange.value" />
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

  <CmkCatalogPanel :title="_t('Additional graph options')" :open="false">
    <GraphRenderOptions
      v-model:horizontal-axis="handler.horizontalAxis.value"
      v-model:vertical-axis="handler.verticalAxis.value"
      v-model:vertical-axis-width-mode="handler.verticalAxisWidthMode.value"
      v-model:fixed-vertical-axis-width="handler.fixedVerticalAxisWidth.value"
      v-model:font-size="handler.fontSize.value"
      v-model:timestamp="handler.timestamp.value"
      v-model:round-margin="handler.roundMargin.value"
      v-model:graph-legend="handler.graphLegend.value"
      v-model:click-to-place-pin="handler.clickToPlacePin.value"
      v-model:show-burger-menu="handler.showBurgerMenu.value"
      v-model:dont-follow-timerange="handler.dontFollowTimerange.value"
    />
  </CmkCatalogPanel>

  <ContentSpacer />
</template>

<style scoped>
.db-custom-graph-widget--preview-placeholder {
  background-color: var(--ux-theme-3);
  height: 240px;
  position: relative;
}

.db-custom-graph-widget--preview-placeholder span {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}
</style>
