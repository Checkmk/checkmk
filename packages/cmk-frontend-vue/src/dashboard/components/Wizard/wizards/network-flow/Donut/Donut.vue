<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkCatalogPanel from 'cmk-ui-library/components/CmkCatalogPanel.vue'
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown'
import type { Suggestions } from 'cmk-ui-library/components/CmkSuggestions'
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

import { MAX_SLICES, useDonut } from './composables/useDonut'

// Explicit multi-word name; the file is Donut.vue to mirror TopTable.vue, but a
// bare "Donut" trips vue/multi-word-component-names.
defineOptions({ name: 'NetworkFlowDonutWizard' })

const { _t } = usei18n()
interface Props extends BaseWidgetProp {
  editWidgetSpec: WidgetSpec | null
}
const props = defineProps<Props>()
const handler = useDonut(props.editWidgetSpec)

const dimensionOptions: Suggestions = {
  type: 'fixed',
  suggestions: [
    { name: 'applications', title: _t('Applications') },
    { name: 'protocols', title: _t('Protocols') }
  ]
}

const legendModeOptions: Suggestions = {
  type: 'fixed',
  suggestions: [
    { name: 'table', title: _t('Table') },
    { name: 'compact', title: _t('Compact') }
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
      widget_id="network-flow-donut-preview"
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
          <FieldDescription>{{ _t('Breakdown dimension') }}</FieldDescription>
          <FieldComponent>
            <CmkDropdown
              v-model="handler.dimension.value"
              :options="dimensionOptions"
              :label="_t('Breakdown dimension')"
            />
          </FieldComponent>
        </TableFormRow>
        <TableFormRow>
          <FieldDescription>{{ _t('Limit to') }}</FieldDescription>
          <FieldComponent>
            <CmkInput
              v-model="handler.limitTo.value as number"
              type="number"
              :unit="_t('slices (max. %{max_slices})', { max_slices: `${MAX_SLICES}` })"
              :external-errors="handler.limitToValidationErrors.value"
            />
          </FieldComponent>
        </TableFormRow>
        <TableFormRow>
          <FieldDescription>{{ _t('Legend style') }}</FieldDescription>
          <FieldComponent>
            <CmkDropdown
              v-model="handler.legendMode.value"
              :options="legendModeOptions"
              :label="_t('Legend style')"
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
