<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkCatalogPanel from 'cmk-ui-library/components/CmkCatalogPanel.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

import ContentSpacer from '@/dashboard/components/ContentSpacer.vue'
import ContextualLinkConfig from '@/dashboard/components/Wizard/components/ContextualLink/ContextualLinkConfig.vue'

import WidgetVisualization from '../../../../components/WidgetVisualization/WidgetVisualization.vue'
import { type UseInventory } from './useInventory'

const { _t } = usei18n()

const handler = defineModel<UseInventory>('handler', { required: true })

defineExpose({ validate })

function validate(): boolean {
  return handler.value.validate()
}
</script>

<template>
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

  <CmkCatalogPanel :title="_t('Contextual link')" variant="padded">
    <ContextualLinkConfig
      v-model:handler="handler.contextualLink"
      :default-target="_t('Inventory of host')"
    />
  </CmkCatalogPanel>
</template>
