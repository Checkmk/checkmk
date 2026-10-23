<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkCatalogPanel from 'cmk-ui-library/components/CmkCatalogPanel.vue'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import CmkLabelRequired from 'cmk-ui-library/components/user-input/CmkLabelRequired.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

import ContentSpacer from '@/dashboard/components/ContentSpacer.vue'
import DashboardPreviewContent from '@/dashboard/components/DashboardPreviewContent.vue'
import FieldComponent from '@/dashboard/components/Wizard/components/TableForm/FieldComponent.vue'
import FieldDescription from '@/dashboard/components/Wizard/components/TableForm/FieldDescription.vue'
import TableFormRow from '@/dashboard/components/Wizard/components/TableForm/TableFormRow.vue'
import WidgetVisualization from '@/dashboard/components/Wizard/components/WidgetVisualization/WidgetVisualization.vue'
import type { BaseWidgetProp, WidgetProps } from '@/dashboard/components/Wizard/types'
import DataSettings from '@/dashboard/components/Wizard/wizards/other/stage1/DataSettings.vue'
import type { GetValidWidgetProps } from '@/dashboard/components/Wizard/wizards/other/types'
import type { WidgetSpec } from '@/dashboard/types/widget'

import { useEmbeddedURL } from './composables/useEmbeddedURL'

const { _t } = usei18n()
interface Props extends BaseWidgetProp {
  editWidgetSpec: WidgetSpec | null
}
const props = defineProps<Props>()
const handler = useEmbeddedURL(props.editWidgetSpec)

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
      widget_id="embedded-url-preview"
      :dashboard-key="dashboardKey"
      :tick="tick"
      :range="range"
      :general_settings="handler.widgetProps.value.general_settings!"
      :content="handler.widgetProps.value.content!"
      :effective-title="handler.widgetProps.value!.effectiveTitle"
      :effective_filter_context="handler.widgetProps.value.effective_filter_context!"
    />

    <ContentSpacer />

    <DataSettings>
      <TableFormRow>
        <FieldDescription>
          {{ _t('Enter URL to embed') }}<CmkLabelRequired space="before" />
        </FieldDescription>
        <FieldComponent>
          <CmkInput
            v-model="handler.url.value"
            type="text"
            field-size="fill"
            :aria-label="_t('Enter URL to embed')"
            :external-errors="handler.urlValidationErrors.value"
          />
        </FieldComponent>
      </TableFormRow>
      <TableFormRow>
        <FieldDescription>{{ _t('Include query parameters for') }}</FieldDescription>
        <FieldComponent>
          <div class="field-component__item">
            <CmkCheckbox v-model="handler.includeContext.value" :label="_t('Dashboard filters')" />
          </div>
          <div class="field-component__item">
            <CmkCheckbox v-model="handler.includeTimeRange.value" :label="_t('Time range')" />
          </div>
        </FieldComponent>
      </TableFormRow>
    </DataSettings>

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
