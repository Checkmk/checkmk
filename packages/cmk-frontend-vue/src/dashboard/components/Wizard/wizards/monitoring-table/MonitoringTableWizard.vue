<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { DateTimeRange } from 'cmk-ui-library/components/date-time'
import { useFilterDefinitions } from 'cmk-ui-library/components/filter'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, h, ref, watch } from 'vue'

import ContentSpacer from '@/dashboard/components/ContentSpacer.vue'
import AddFilters from '@/dashboard/components/Wizard/components/AddFilters/AddFilters.vue'
import FiltersRecap from '@/dashboard/components/Wizard/components/FiltersRecap/FiltersRecap.vue'
import { parseContextConfiguredFilters } from '@/dashboard/components/Wizard/components/FiltersRecap/utils'
import { useWidgetVisualizationProps } from '@/dashboard/components/Wizard/components/WidgetVisualization/useWidgetVisualization'
import { useWidgetFilterManager } from '@/dashboard/components/Wizard/components/filter/composables/useWidgetFilterManager.ts'
import { extractConfiguredFilters } from '@/dashboard/components/Wizard/utils'
import type { DashboardKey } from '@/dashboard/types/dashboard'
import type { ContextFilters } from '@/dashboard/types/filter.ts'
import type {
  MonitoringTableContent,
  WidgetContent,
  WidgetFilterContext,
  WidgetGeneralSettings,
  WidgetSpec
} from '@/dashboard/types/widget'
import type { MonitoringTableName } from '@/monitoring/table-widget/tableDescriptors'
import QuickSetup from '@/quick-setup/components/quick-setup/QuickSetup.vue'
import type { QuickSetupStageSpec } from '@/quick-setup/components/quick-setup/quick_setup_types'
import useWizard from '@/quick-setup/components/quick-setup/useWizard'

import CloseButton from '../../components/CloseButton.vue'
import StepsHeader from '../../components/StepsHeader.vue'
import WizardContainer from '../../components/WizardContainer.vue'
import WizardStageContainer from '../../components/WizardStageContainer.vue'
import WizardStepsContainer from '../../components/WizardStepsContainer.vue'
import {
  defaultMonitoringTableContent,
  filtersForeignTo,
  monitoringTableViews
} from './monitoringTables'
import Stage1 from './stage1/StageContents.vue'
import Stage2 from './stage2/StageContents.vue'
import Stage3 from './stage3/StageContents.vue'

const { _t } = usei18n()

interface MonitoringTableWizardProps {
  tick: number
  range: DateTimeRange
  dashboardKey: DashboardKey
  contextFilters: ContextFilters
  editWidgetSpec?: WidgetSpec | null
}

const props = withDefaults(defineProps<MonitoringTableWizardProps>(), {
  editWidgetSpec: null
})

const emit = defineEmits<{
  goBack: []
  close: []
  addWidget: [
    content: WidgetContent,
    generalSettings: WidgetGeneralSettings,
    filterContext: WidgetFilterContext
  ]
}>()

const views = monitoringTableViews()

const content = ref<MonitoringTableContent | null>(
  props.editWidgetSpec?.content.type === 'monitoring_table'
    ? (props.editWidgetSpec.content as MonitoringTableContent)
    : null
)
const table = ref<MonitoringTableName | null>(content.value?.table ?? null)
const infos = computed(() => (table.value === null ? [] : views[table.value].infos))

const filterDefinitions = useFilterDefinitions()
const widgetFilterManager = useWidgetFilterManager(
  props.editWidgetSpec?.filter_context.filters ?? {},
  filterDefinitions
)

const visualizationProps = useWidgetVisualizationProps(
  '$DEFAULT_TITLE$',
  props.editWidgetSpec?.general_settings,
  'monitoring_table'
)

const validationError = ref<string | undefined>()

watch(table, (newTable) => {
  validationError.value = undefined
  if (newTable === null || newTable === content.value?.table) {
    return
  }
  widgetFilterManager.closeSelectionMenu()
  filtersForeignTo(
    newTable,
    widgetFilterManager.getSelectedFilters(),
    (filterId) => filterDefinitions[filterId]?.extensions.info
  ).forEach((filterId) => widgetFilterManager.filterHandler.removeFilter(filterId))
  content.value = defaultMonitoringTableContent(newTable)
})

const wizardHandler = useWizard(3)
const wizardStages: QuickSetupStageSpec[] = [
  { title: _t('Data selection'), actions: [], errors: [] },
  { title: _t('Data configuration'), actions: [], errors: [] },
  { title: _t('Visualization'), actions: [], errors: [] }
]

const currentFilterSelectionFocus = computed(() =>
  widgetFilterManager.selectionMenuOpen.value
    ? widgetFilterManager.selectionMenuCurrentTarget.value
    : null
)

function stage1GoNext() {
  if (table.value === null) {
    validationError.value = _t('Please select a view.')
    return
  }
  widgetFilterManager.closeSelectionMenu()
  wizardStages[0]!.recapContent = h(FiltersRecap, {
    customValue: views[table.value].title,
    customValueTitle: _t('View'),
    contextConfiguredFilters: parseContextConfiguredFilters(props.contextFilters),
    widgetFilters: extractConfiguredFilters(widgetFilterManager)
  })
  wizardHandler.next()
}

function saveWidget() {
  if (!content.value || !visualizationProps.validate()) {
    return
  }
  emit('addWidget', content.value, visualizationProps.widgetGeneralSettings.value, {
    uses_infos: infos.value,
    filters: extractConfiguredFilters(widgetFilterManager)
  } as WidgetFilterContext)
}
</script>

<template>
  <WizardContainer>
    <WizardStepsContainer v-if="widgetFilterManager.selectionMenuOpen.value">
      <AddFilters
        :filter-selection-target="widgetFilterManager.selectionMenuCurrentTarget.value"
        :close="widgetFilterManager.closeSelectionMenu"
        :filters="widgetFilterManager.filterHandler"
      />
    </WizardStepsContainer>
    <WizardStepsContainer v-else>
      <StepsHeader :title="_t('View')" :subtitle="_t('Define widget')" @back="emit('goBack')" />

      <ContentSpacer />

      <QuickSetup
        :loading="false"
        :current-stage="wizardHandler.stage.value"
        :regular-stages="wizardStages"
        :mode="wizardHandler.mode"
        :prevent-leaving="false"
        :hide-wait-icon="true"
      />
    </WizardStepsContainer>

    <WizardStageContainer size="large">
      <CloseButton @close="emit('close')" />
      <Stage1
        v-if="wizardHandler.stage.value === 0"
        v-model:table="table"
        :widget-configured-filters="widgetFilterManager.getConfiguredFilters()"
        :widget-active-filters="widgetFilterManager.getSelectedFilters()"
        :context-filters="contextFilters"
        :current-filter-selection-menu-focus="currentFilterSelectionFocus"
        :validation-error="validationError"
        @go-next="stage1GoNext"
        @set-focus="widgetFilterManager.openSelectionMenu"
        @update-filter-values="
          (filterId, values) => widgetFilterManager.updateFilterValues(filterId, values)
        "
        @remove-filter="(filterId) => widgetFilterManager.filterHandler.removeFilter(filterId)"
      />
      <Stage2
        v-if="wizardHandler.stage.value === 1"
        @go-prev="wizardHandler.prev"
        @go-next="wizardHandler.next"
      />
      <Stage3
        v-if="wizardHandler.stage.value === 2"
        :is-edit-mode="!!editWidgetSpec"
        @go-prev="wizardHandler.prev"
        @add-widget="saveWidget"
      />
    </WizardStageContainer>
  </WizardContainer>
</template>
