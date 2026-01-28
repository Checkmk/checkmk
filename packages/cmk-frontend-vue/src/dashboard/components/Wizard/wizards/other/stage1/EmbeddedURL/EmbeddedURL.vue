<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkCatalogPanel from '@/components/CmkCatalogPanel.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'

import DashboardPreviewContent from '@/dashboard/components/DashboardPreviewContent.vue'
import ContentSpacer from '@/dashboard/components/Wizard/components/ContentSpacer.vue'
import WidgetVisualization from '@/dashboard/components/Wizard/components/WidgetVisualization/WidgetVisualization.vue'
import type { BaseWidgetProp, WidgetProps } from '@/dashboard/components/Wizard/types'
import DataSettings from '@/dashboard/components/Wizard/wizards/other/stage1/DataSettings.vue'
import type { GetValidWidgetProps } from '@/dashboard/components/Wizard/wizards/other/types'
import type { DashboardConstants } from '@/dashboard/types/dashboard'
import type { WidgetSpec } from '@/dashboard/types/widget'

import { useEmbeddedURL } from './composables/useEmbeddedURL'

const { _t } = usei18n()
interface Props extends BaseWidgetProp {
  dashboardConstants: DashboardConstants
  editWidgetSpec: WidgetSpec | null
}
const props = defineProps<Props>()
const handler = useEmbeddedURL(props.dashboardConstants, props.editWidgetSpec)

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
      :general_settings="handler.widgetProps.value.general_settings!"
      :content="handler.widgetProps.value.content!"
      :effective-title="handler.widgetProps.value!.effectiveTitle"
      :effective_filter_context="handler.widgetProps.value.effective_filter_context!"
    />

    <ContentSpacer />

    <DataSettings :label="_t('Enter URL to embed')">
      <CmkInput v-model="handler.url.value" type="text" field-size="LARGE" />
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
      />
    </CmkCatalogPanel>

    <ContentSpacer />
  </div>
</template>
