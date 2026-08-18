<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkCatalogPanel from 'cmk-ui-library/components/CmkCatalogPanel.vue'
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown'
import type { Suggestions } from 'cmk-ui-library/components/CmkSuggestions'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

import ContentSpacer from '@/dashboard/components/ContentSpacer.vue'
import DashboardPreviewContent from '@/dashboard/components/DashboardPreviewContent.vue'
import FieldComponent from '@/dashboard/components/Wizard/components/TableForm/FieldComponent.vue'
import FieldDescription from '@/dashboard/components/Wizard/components/TableForm/FieldDescription.vue'
import TableForm from '@/dashboard/components/Wizard/components/TableForm/TableForm.vue'
import TableFormRow from '@/dashboard/components/Wizard/components/TableForm/TableFormRow.vue'
import WidgetVisualization from '@/dashboard/components/Wizard/components/WidgetVisualization/WidgetVisualization.vue'
import type { BaseWidgetProp, WidgetProps } from '@/dashboard/components/Wizard/types'
import type { GetValidWidgetProps } from '@/dashboard/components/Wizard/wizards/network-flow/types'
import type { WidgetSpec } from '@/dashboard/types/widget'

import { MAX_SERIES, useTrendChart } from './composables/useTrendChart'

// Explicit multi-word name; the file is TrendChart.vue to mirror the sibling
// wizards, but a bare "TrendChart" trips vue/multi-word-component-names.
defineOptions({ name: 'NetworkFlowTrendChartWizard' })

const { _t } = usei18n()
interface Props extends BaseWidgetProp {
  editWidgetSpec: WidgetSpec | null
}
const props = defineProps<Props>()
const handler = useTrendChart(props.editWidgetSpec)

const dimensionOptions: Suggestions = {
  type: 'fixed',
  suggestions: [
    { name: 'applications', title: _t('Applications') },
    { name: 'autonomous_systems', title: _t('Autonomous systems') },
    { name: 'total_bandwidth', title: _t('Total bandwidth') }
  ]
}

const displayModeOptions: Suggestions = {
  type: 'fixed',
  suggestions: [
    { name: 'lines', title: _t('Lines') },
    { name: 'stacked_area', title: _t('Stacked area') }
  ]
}

function getValidWidgetProps(): WidgetProps | null {
  if (handler.validate()) {
    return handler.widgetProps.value
  }
  return null
}
defineExpose<GetValidWidgetProps>({ getValidWidgetProps })
</script>

<template>
  <div>
    <DashboardPreviewContent
      widget_id="network-flow-trend-chart-preview"
      :dashboard-key="dashboardKey"
      :general_settings="handler.widgetProps.value.general_settings!"
      :content="handler.widgetProps.value.content!"
      :effective-title="handler.widgetProps.value!.effectiveTitle"
      :effective_filter_context="handler.widgetProps.value.effective_filter_context!"
    />

    <ContentSpacer />

    <CmkCatalogPanel :title="_t('Data settings')" variant="padded">
      <TableForm>
        <TableFormRow>
          <FieldDescription>{{ _t('Series dimension') }}</FieldDescription>
          <FieldComponent>
            <CmkDropdown
              v-model="handler.dimension.value"
              :options="dimensionOptions"
              :label="_t('Series dimension')"
            />
          </FieldComponent>
        </TableFormRow>
        <TableFormRow>
          <FieldDescription>{{ _t('Display mode') }}</FieldDescription>
          <FieldComponent>
            <CmkDropdown
              v-model="handler.displayMode.value"
              :options="displayModeOptions"
              :label="_t('Display mode')"
            />
          </FieldComponent>
        </TableFormRow>
        <!-- Total bandwidth is a fixed two-series (ingress/egress) view, so a
             top-N limit does not apply to it. -->
        <TableFormRow v-if="handler.dimension.value !== 'total_bandwidth'">
          <FieldDescription>{{ _t('Limit to') }}</FieldDescription>
          <FieldComponent>
            <CmkInput
              v-model="handler.limitTo.value as number"
              type="number"
              :unit="_t('series (max. %{max_series})', { max_series: `${MAX_SERIES}` })"
              :external-errors="handler.limitToValidationErrors.value"
            />
          </FieldComponent>
        </TableFormRow>
        <TableFormRow>
          <FieldDescription>{{ _t('Legend') }}</FieldDescription>
          <FieldComponent>
            <CmkCheckbox
              v-model="handler.showLegend.value"
              :label="_t('List the plotted series below the graph')"
            />
          </FieldComponent>
        </TableFormRow>
      </TableForm>
    </CmkCatalogPanel>

    <ContentSpacer :dimension="6" />

    <CmkCatalogPanel :title="_t('Widget settings')" variant="padded">
      <WidgetVisualization
        v-model:show-title="handler.showTitle.value"
        v-model:show-title-background="handler.showTitleBackground.value"
        v-model:show-widget-background="handler.showWidgetBackground.value"
        v-model:title="handler.title.value"
        v-model:title-url="handler.titleUrl.value"
        v-model:title-url-enabled="handler.titleUrlEnabled.value"
        v-model:title-url-validation-errors="handler.titleUrlValidationErrors.value"
        :title-macros="handler.titleMacros.value"
      />
    </CmkCatalogPanel>

    <ContentSpacer />
  </div>
</template>
