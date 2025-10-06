<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkCollapsible from '@/components/CmkCollapsible.vue'
import CmkCollapsibleTitle from '@/components/CmkCollapsibleTitle.vue'
import CmkIndent from '@/components/CmkIndent.vue'
import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'

import DashboardPreviewContent from '@/dashboard-wip/components/DashboardPreviewContent.vue'
import ContentSpacer from '@/dashboard-wip/components/Wizard/components/ContentSpacer.vue'
import RadioButton from '@/dashboard-wip/components/Wizard/components/RadioButton.vue'
import FieldComponent from '@/dashboard-wip/components/Wizard/components/TableForm/FieldComponent.vue'
import FieldDescription from '@/dashboard-wip/components/Wizard/components/TableForm/FieldDescription.vue'
import TableForm from '@/dashboard-wip/components/Wizard/components/TableForm/TableForm.vue'
import TableFormRow from '@/dashboard-wip/components/Wizard/components/TableForm/TableFormRow.vue'
import WidgetVisualization from '@/dashboard-wip/components/Wizard/components/WidgetVisualization/WidgetVisualization.vue'
import type { BaseWidgetProp } from '@/dashboard-wip/components/Wizard/types'

import type { UseServiceState } from './composables/useServiceState'

const { _t } = usei18n()
defineProps<BaseWidgetProp>()
const handler = defineModel<UseServiceState>('handler', { required: true })

const displayDataSettings = ref<boolean>(true)
const displayVisualizationSettings = ref<boolean>(true)
const widgetProps = computed(() => handler.value.widgetProps)
</script>

<template>
  <DashboardPreviewContent
    widget_id="host-state-preview"
    :dashboard-name="dashboardName"
    :general_settings="widgetProps.value!.general_settings!"
    :content="widgetProps.value!.content!"
    :effective_filter_context="widgetProps.value!.effective_filter_context!"
  />

  <ContentSpacer />

  <CmkCollapsibleTitle
    :title="_t('Data settings')"
    :open="displayDataSettings"
    class="collapsible"
    @toggle-open="displayDataSettings = !displayDataSettings"
  />
  <CmkCollapsible :open="displayDataSettings">
    <TableForm>
      <TableFormRow>
        <FieldDescription>{{ _t('Host status') }}</FieldDescription>
        <FieldComponent>
          <div class="db-service-state__item">
            <CmkCheckbox
              v-model="handler.showBackgroundInStatusColorAndLabel.value"
              :label="_t('Show background in status color and label')"
            />
          </div>
          <div class="db-service-state__item">
            <CmkIndent>
              <div class="db-service-state__item">
                <RadioButton
                  v-model="handler.colorizeStates.value"
                  name="colorize"
                  value="all"
                  :label="_t('Colorize all states')"
                />
              </div>

              <div class="db-service-state__item">
                <RadioButton
                  v-model="handler.colorizeStates.value"
                  name="colorize"
                  value="not_ok"
                  :label="_t('Colorize not OK states')"
                />
              </div>
            </CmkIndent>
          </div>
        </FieldComponent>
      </TableFormRow>

      <TableFormRow>
        <FieldDescription>{{ _t('Summary') }}</FieldDescription>
        <FieldComponent>
          <FieldComponent>
            <CmkCheckbox
              v-model="handler.showSummaryForNotOKStates.value"
              :label="_t('Show summary for not OK states')"
            />
          </FieldComponent>
        </FieldComponent>
      </TableFormRow>
    </TableForm>
  </CmkCollapsible>

  <ContentSpacer />

  <CmkCollapsibleTitle
    :title="_t('Widget visualization')"
    :open="displayVisualizationSettings"
    class="collapsible"
    @toggle-open="displayVisualizationSettings = !displayVisualizationSettings"
  />
  <CmkCollapsible :open="displayVisualizationSettings">
    <WidgetVisualization
      v-model:show-title="handler.showTitle.value"
      v-model:show-title-background="handler.showTitleBackground.value"
      v-model:show-widget-background="handler.showWidgetBackground.value"
      v-model:title="handler.title.value"
      v-model:title-url="handler.titleUrl.value"
      v-model:title-url-enabled="handler.titleUrlEnabled.value"
      v-model:title-url-validation-errors="handler.titleUrlValidationErrors.value"
    />
  </CmkCollapsible>

  <ContentSpacer />
</template>

<style scoped>
.db-service-state__item {
  display: block;
  padding-bottom: var(--spacing-half);
}
</style>
