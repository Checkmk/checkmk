<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref } from 'vue'

import usei18n, { untranslated } from '@/lib/i18n'

import DashboardPreviewContent from '@/dashboard-wip/components/DashboardPreviewContent.vue'
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

import type { UseHostStateSummary } from './composables/useHostStateSummary'

const { _t } = usei18n()
defineProps<BaseWidgetProp>()
const handler = defineModel<UseHostStateSummary>('handler', { required: true })

const displayDataSettings = ref<boolean>(true)
const displayVisualizationSettings = ref<boolean>(true)

// [value, label]
const states: [string, string][] = [
  ['UP', 'UP'],
  ['DOWN', 'DOWN'],
  ['UNREACH', 'UNREACH']
]
const widgetProps = computed(() => handler.value.widgetProps)
</script>

<template>
  <DashboardPreviewContent
    widget_id="host-state-summary-preview"
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
        <FieldDescription>{{ _t('Selected state') }}</FieldDescription>
        <FieldComponent>
          <div v-for="[value, label] of states" :key="value" class="db-host-state-summary__item">
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
  </CollapsibleContent>

  <ContentSpacer />

  <CollapsibleTitle
    :title="_t('Widget visualization')"
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

<style scoped>
.db-host-state-summary__item {
  display: block;
  padding-bottom: 5px;
}
</style>
