<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { ConfiguredFilters } from 'cmk-ui-library/components/filter'

import type { BaseWidgetProp } from '@/dashboard/components/Wizard/types'
import type {
  WidgetContent,
  WidgetFilterContext,
  WidgetGeneralSettings
} from '@/dashboard/types/widget'

import Stage2Header from '../../../../components/Stage2Header.vue'
import type { UseEmbeddedCustomGraph } from '../composables/useEmbeddedCustomGraph'
import EmbeddedCustomGraphWidget from './EmbeddedCustomGraphWidget.vue'

const { filters } = defineProps<
  BaseWidgetProp & {
    filters: ConfiguredFilters
    edit: boolean
  }
>()

const handler = defineModel<UseEmbeddedCustomGraph>('handler', { required: true })

const emit = defineEmits<{
  goPrev: []
  addWidget: [
    content: WidgetContent,
    generalSettings: WidgetGeneralSettings,
    filterContext: WidgetFilterContext
  ]
}>()

async function addWidget(): Promise<void> {
  if (!handler.value.validate()) {
    return
  }
  const saved = await handler.value.computeWidgetProps(filters)
  emit('addWidget', saved.content, saved.general_settings, saved.effective_filter_context)
}
</script>

<template>
  <Stage2Header :edit="edit" @back="emit('goPrev')" @save="addWidget" />

  <EmbeddedCustomGraphWidget
    v-model:handler="handler"
    :dashboard-key="dashboardKey"
    :tick="tick"
    :range="range"
    :filters="filters"
  />
</template>
