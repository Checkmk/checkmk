<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import CmkCatalogPanel from '@/components/CmkCatalogPanel.vue'

import DashboardPreviewContent from '@/dashboard/components/DashboardPreviewContent.vue'
import ContentSpacer from '@/dashboard/components/Wizard/components/ContentSpacer.vue'
import DataRangeInput from '@/dashboard/components/Wizard/components/DataRangeInput/DataRangeInput.vue'
import FieldComponent from '@/dashboard/components/Wizard/components/TableForm/FieldComponent.vue'
import FieldDescription from '@/dashboard/components/Wizard/components/TableForm/FieldDescription.vue'
import TableForm from '@/dashboard/components/Wizard/components/TableForm/TableForm.vue'
import TableFormRow from '@/dashboard/components/Wizard/components/TableForm/TableFormRow.vue'
import WidgetVisualization from '@/dashboard/components/Wizard/components/WidgetVisualization/WidgetVisualization.vue'
import type { BaseWidgetProp } from '@/dashboard/components/Wizard/types.ts'

import type { UseBarplot } from './composables/useBarplot.ts'

const { _t } = usei18n()

defineProps<BaseWidgetProp>()

const handler = defineModel<UseBarplot>('handler', { required: true })

const widgetProps = computed(() => handler.value.widgetProps)
</script>

<template>
  <DashboardPreviewContent
    widget_id="barplot-preview"
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
        <FieldDescription>{{ _t('Data range') }}</FieldDescription>
        <FieldComponent>
          <DataRangeInput
            v-model:data-range-type="handler.dataRangeType.value"
            v-model:data-range-symbol="handler.dataRangeSymbol.value"
            v-model:data-range-min="handler.dataRangeMin.value"
            v-model:data-range-max="handler.dataRangeMax.value"
          />
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
