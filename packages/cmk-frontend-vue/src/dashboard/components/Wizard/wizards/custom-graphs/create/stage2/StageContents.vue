<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { ConfiguredFilters } from 'cmk-ui-library/components/filter'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref } from 'vue'

import type { BaseWidgetProp, WidgetContentType } from '@/dashboard/components/Wizard/types'
import { useInjectCustomGraphPermissions } from '@/dashboard/composables/useProvideCustomGraphPermissions'
import type {
  CustomGraphContent,
  WidgetContent,
  WidgetFilterContext,
  WidgetGeneralSettings
} from '@/dashboard/types/widget'

import ActionButton from '../../../../components/ActionButton.vue'
import Stage2Header from '../../../../components/Stage2Header.vue'
import type { EmbeddedGraphDefinition } from '../../editor/types'
import type { UseEmbeddedCustomGraph } from '../composables/useEmbeddedCustomGraph'
import EmbeddedCustomGraphWidget from './EmbeddedCustomGraphWidget.vue'
import SaveToCatalogPopup from './SaveToCatalogPopup.vue'

const { _t } = usei18n()

const { filters, catalogNameBase } = defineProps<
  BaseWidgetProp & {
    filters: ConfiguredFilters
    edit: boolean
    /** Starting point of the ID suggested when saving to the catalog. */
    catalogNameBase?: string | undefined
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

const { edit: mayEditCustomGraph } = useInjectCustomGraphPermissions()
const isSaveToCatalogOpen = ref(false)
const catalogDefinition = computed<EmbeddedGraphDefinition>(() => ({
  data_sources: [...handler.value.dataSources.value],
  graph_options: handler.value.graphOptions.value
}))

async function emitWidget(content?: WidgetContentType): Promise<void> {
  const saved = await handler.value.computeWidgetProps(filters, content)
  emit('addWidget', saved.content, saved.general_settings, saved.effective_filter_context)
}

async function addWidget(): Promise<void> {
  if (!handler.value.validate()) {
    return
  }
  await emitWidget()
}

function openSaveToCatalog(): void {
  if (handler.value.validate()) {
    isSaveToCatalogOpen.value = true
  }
}

// The saved graph replaces the embedded one: the widget links it from now on.
async function addLinkedWidget(graphName: string): Promise<void> {
  isSaveToCatalogOpen.value = false
  const linked: CustomGraphContent = {
    type: 'custom_graph',
    custom_graph: graphName,
    timerange: handler.value.content().timerange,
    graph_render_options: handler.value.renderOptions.graphRenderOptions.value
  }
  await emitWidget(linked)
}
</script>

<template>
  <Stage2Header :edit="edit" @back="emit('goPrev')" @save="addWidget">
    <template v-if="mayEditCustomGraph" #actions>
      <ActionButton
        :label="_t('Save to graph catalog')"
        :action="openSaveToCatalog"
        variant="optional"
      />
    </template>
  </Stage2Header>

  <EmbeddedCustomGraphWidget
    v-model:handler="handler"
    :dashboard-key="dashboardKey"
    :tick="tick"
    :range="range"
    :filters="filters"
  />

  <SaveToCatalogPopup
    v-if="mayEditCustomGraph && isSaveToCatalogOpen"
    :definition="catalogDefinition"
    :name-base="catalogNameBase"
    :edit="edit"
    @saved="addLinkedWidget"
    @close="isSaveToCatalogOpen = false"
  />
</template>
