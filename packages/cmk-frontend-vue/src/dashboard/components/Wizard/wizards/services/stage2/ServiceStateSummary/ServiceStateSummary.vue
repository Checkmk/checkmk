<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n, { untranslated } from '@/lib/i18n'

import CmkCatalogPanel from '@/components/CmkCatalogPanel.vue'

import DashboardPreviewContent from '@/dashboard/components/DashboardPreviewContent.vue'
import ContentSpacer from '@/dashboard/components/Wizard/components/ContentSpacer.vue'
import RadioButton from '@/dashboard/components/Wizard/components/RadioButton.vue'
import FieldComponent from '@/dashboard/components/Wizard/components/TableForm/FieldComponent.vue'
import FieldDescription from '@/dashboard/components/Wizard/components/TableForm/FieldDescription.vue'
import TableForm from '@/dashboard/components/Wizard/components/TableForm/TableForm.vue'
import TableFormRow from '@/dashboard/components/Wizard/components/TableForm/TableFormRow.vue'
import WidgetVisualization from '@/dashboard/components/Wizard/components/WidgetVisualization/WidgetVisualization.vue'
import type { BaseWidgetProp } from '@/dashboard/components/Wizard/types'

import type { UseServiceStateSummary } from './composables/useServiceStateSummary'

const { _t } = usei18n()
defineProps<BaseWidgetProp>()
const handler = defineModel<UseServiceStateSummary>('handler', { required: true })

// [value, label]
const states: [string, string][] = [
  ['OK', 'OK'],
  ['WARNING', 'WARN'],
  ['CRITICAL', 'CRIT'],
  ['UNKNOWN', 'UNKNOWN']
]

const widgetProps = computed(() => handler.value.widgetProps)
</script>

<template>
  <DashboardPreviewContent
    widget_id="host-state-summary-preview"
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
        <FieldDescription>{{ _t('Selected state') }}</FieldDescription>
        <FieldComponent>
          <div v-for="[value, label] of states" :key="value" class="db-service-state-summary__item">
            <RadioButton
              v-model="handler.selectedState.value"
              :value="value"
              :label="untranslated(label)"
              name="selected_state"
            />
          </div>
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
.db-service-state-summary__item {
  display: block;
  padding-bottom: 5px;
}
</style>
