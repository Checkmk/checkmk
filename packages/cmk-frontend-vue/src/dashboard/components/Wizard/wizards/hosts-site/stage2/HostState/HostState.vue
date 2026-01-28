<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import CmkCatalogPanel from '@/components/CmkCatalogPanel.vue'
import CmkIndent from '@/components/CmkIndent.vue'
import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'

import DashboardPreviewContent from '@/dashboard/components/DashboardPreviewContent.vue'
import ContentSpacer from '@/dashboard/components/Wizard/components/ContentSpacer.vue'
import RadioButton from '@/dashboard/components/Wizard/components/RadioButton.vue'
import FieldComponent from '@/dashboard/components/Wizard/components/TableForm/FieldComponent.vue'
import FieldDescription from '@/dashboard/components/Wizard/components/TableForm/FieldDescription.vue'
import TableForm from '@/dashboard/components/Wizard/components/TableForm/TableForm.vue'
import TableFormRow from '@/dashboard/components/Wizard/components/TableForm/TableFormRow.vue'
import WidgetVisualization from '@/dashboard/components/Wizard/components/WidgetVisualization/WidgetVisualization.vue'
import type { BaseWidgetProp } from '@/dashboard/components/Wizard/types'

import type { UseHostState } from './composables/useHostState'

const { _t } = usei18n()
defineProps<BaseWidgetProp>()
const handler = defineModel<UseHostState>('handler', { required: true })

const widgetProps = computed(() => handler.value.widgetProps)
</script>

<template>
  <DashboardPreviewContent
    widget_id="host-state-preview"
    :dashboard-key="dashboardKey"
    :general_settings="widgetProps.value!.general_settings!"
    :content="widgetProps.value!.content!"
    :effective-title="widgetProps.value!.effectiveTitle"
    :effective_filter_context="widgetProps.value!.effective_filter_context!"
  />

  <ContentSpacer />

  <CmkCatalogPanel :title="_t('Data settings')" variant="padded">
    <TableForm>
      <TableFormRow>
        <FieldDescription>{{ _t('Host status') }}</FieldDescription>
        <FieldComponent>
          <div class="db-host-state__item">
            <CmkCheckbox
              v-model="handler.showBackgroundInStatusColorAndLabel.value"
              :label="_t('Show background in status color and label')"
            />
          </div>
          <div v-if="handler.showBackgroundInStatusColorAndLabel.value" class="db-host-state__item">
            <CmkIndent>
              <div class="db-host-state__item">
                <RadioButton
                  v-model="handler.colorizeStates.value"
                  name="colorize"
                  value="all"
                  :label="_t('Colorize all states')"
                />
              </div>

              <div class="db-host-state__item">
                <RadioButton
                  v-model="handler.colorizeStates.value"
                  name="colorize"
                  value="not_ok"
                  :label="_t('Colorize not UP states')"
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
              v-model="handler.showSummaryForNonUpStates.value"
              :label="_t('Show summary for not UP states')"
            />
          </FieldComponent>
        </FieldComponent>
      </TableFormRow>
    </TableForm>
  </CmkCatalogPanel>

  <ContentSpacer />

  <CmkCatalogPanel :title="_t('Widget settings')" variant="padded">
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
.db-host-state__item {
  display: block;
  padding-bottom: var(--spacing-half);
}
</style>
