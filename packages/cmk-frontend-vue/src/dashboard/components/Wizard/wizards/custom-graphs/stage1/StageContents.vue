<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import type { DateTimeRange } from 'cmk-ui-library/components/date-time'
import type { ConfiguredFilters } from 'cmk-ui-library/components/filter'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed, ref, toValue } from 'vue'

import ContentSpacer from '@/dashboard/components/ContentSpacer.vue'
import { useInjectCustomGraphPermissions } from '@/dashboard/composables/useProvideCustomGraphPermissions'
import type { DashboardKey } from '@/dashboard/types/dashboard'
import type {
  WidgetContent,
  WidgetFilterContext,
  WidgetGeneralSettings,
  WidgetSpec
} from '@/dashboard/types/widget'
import { listCustomGraphMetadata } from '@/graphing/designer/api'

import ActionBar from '../../../components/ActionBar.vue'
import ActionButton from '../../../components/ActionButton.vue'
import CustomGraphWidget from './CustomGraphWidget.vue'
import { useCustomGraph } from './composables/useCustomGraph'

const { _t } = usei18n()

interface Stage1Props {
  tick: number
  range: DateTimeRange
  dashboardKey: DashboardKey
  filters: ConfiguredFilters
  editWidgetSpec: WidgetSpec | null
}

const props = defineProps<Stage1Props>()
// Injected before the first await, which ends the setup context.
const { edit: mayEditCustomGraph } = useInjectCustomGraphPermissions()

const handler = await useCustomGraph(props.filters, props.editWidgetSpec || undefined)

const emit = defineEmits<{
  addWidget: [
    content: WidgetContent,
    generalSettings: WidgetGeneralSettings,
    filterContext: WidgetFilterContext
  ]
  /** Replace the linked graph with an editable copy of it. */
  cloneGraph: [name: string]
}>()

const addWidget = async () => {
  if (!handler.validate()) {
    return
  }
  const submitProps = await handler.getSubmitProps()
  emit(
    'addWidget',
    toValue(submitProps.content),
    toValue(submitProps.general_settings),
    toValue(submitProps.effective_filter_context)
  )
}

const isUpdate = computed(() => props.editWidgetSpec !== null)
const mayClone = isUpdate.value && mayEditCustomGraph

const cloneableGraph = computed(() => (mayClone ? handler.customGraph.value : null))

// The widget stores only the graph's name; without the catalog, the name stands in for the title.
const catalogTitles = ref<Record<string, string>>({})
if (mayClone) {
  void listCustomGraphMetadata()
    .then((collection) => {
      catalogTitles.value = Object.fromEntries(
        collection.value.flatMap((entry) =>
          entry.id === undefined ? [] : [[entry.id, entry.title ?? entry.id]]
        )
      )
    })
    .catch(() => {})
}

const cloneableGraphTitle = computed(() =>
  cloneableGraph.value === null
    ? null
    : (catalogTitles.value[cloneableGraph.value] ?? cloneableGraph.value)
)

function cloneGraph(): void {
  if (cloneableGraph.value !== null) {
    emit('cloneGraph', cloneableGraph.value)
  }
}
</script>

<template>
  <CmkHeading type="h1">
    {{ _t('Custom graph') }}
  </CmkHeading>

  <ContentSpacer />

  <ActionBar align-items="left">
    <ActionButton
      :label="isUpdate ? _t('Save widget') : _t('Add & place widget')"
      :action="addWidget"
      variant="primary"
    />
  </ActionBar>

  <ContentSpacer />

  <CmkAlert
    v-if="cloneableGraphTitle !== null"
    variant="info"
    class="db-stage-contents__alert"
    :heading="_t('Linked to catalog graph “%{title}”', { title: cloneableGraphTitle })"
    :text="
      untranslated(
        `${_t('Changes here affect only this widget.')}\n${_t('Clone the graph to edit the query, metrics or visualization.')}`
      )
    "
    :main-button="{ title: _t('Clone & edit graph'), onclick: cloneGraph }"
  />

  <ContentSpacer />

  <CustomGraphWidget
    v-model:handler="handler"
    :dashboard-key="dashboardKey"
    :tick="tick"
    :range="range"
  />
</template>

<style scoped>
.db-stage-contents__alert {
  margin-top: 0;
  margin-bottom: 0;
}
</style>
