<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, h, onBeforeMount, ref } from 'vue'

import usei18n, { untranslated } from '@/lib/i18n'

import type { Suggestion } from '@/components/CmkSuggestions'

import QuickSetup from '@/quick-setup/components/quick-setup/QuickSetup.vue'
import type { QuickSetupStageSpec } from '@/quick-setup/components/quick-setup/quick_setup_types'
import useWizard from '@/quick-setup/components/quick-setup/useWizard'

import type { ConfiguredFilters } from '../../../../components/filter/types'
import { useFilterDefinitions } from '../../../../components/filter/utils'
import type { DashboardConstants, DashboardKey } from '../../../../types/dashboard'
import type { ContextFilters } from '../../../../types/filter'
import type {
  WidgetContent,
  WidgetFilterContext,
  WidgetGeneralSettings,
  WidgetSpec
} from '../../../../types/widget'
import { dashboardAPI } from '../../../../utils'
import AddFilters from '../../components/AddFilters/AddFilters.vue'
import CloseButton from '../../components/CloseButton.vue'
import ContentSpacer from '../../components/ContentSpacer.vue'
import FiltersRecap from '../../components/FiltersRecap/FiltersRecap.vue'
import { parseContextConfiguredFilters, squashFilters } from '../../components/FiltersRecap/utils'
import StepsHeader from '../../components/StepsHeader.vue'
import WizardContainer from '../../components/WizardContainer.vue'
import WizardStageContainer from '../../components/WizardStageContainer.vue'
import WizardStepsContainer from '../../components/WizardStepsContainer.vue'
import { useWidgetFilterManager } from '../../components/filter/composables/useWidgetFilterManager'
import type { InventoryContent, WidgetContentType, WidgetProps } from '../../types'
import { ElementSelection } from '../../types'
import { generateWidgetProps } from '../../utils'
import Stage1 from './stage1/StageContents.vue'
import Stage2 from './stage2/StageContents.vue'

const { _t } = usei18n()

interface HwSwInventoryWizardProps {
  dashboardKey: DashboardKey
  contextFilters: ContextFilters
  dashboardConstants: DashboardConstants
  editWidgetSpec?: WidgetSpec | null
}

const props = withDefaults(defineProps<HwSwInventoryWizardProps>(), {
  editWidgetSpec: null
})

const emit = defineEmits<{
  goBack: []
  addWidget: [
    content: WidgetContent,
    generalSettings: WidgetGeneralSettings,
    filterContext: WidgetFilterContext
  ]
}>()

const inventoryPaths = ref<Suggestion[]>([])
onBeforeMount(async () => {
  const result = await dashboardAPI.listAvailableInventory()
  inventoryPaths.value = Array.isArray(result.value)
    ? result.value.map((item) => ({
        name: item.id ?? null,
        title: untranslated(item.title ?? '')
      }))
    : []
})

const editWidget = computed<WidgetProps | null>(() => {
  if (!props.editWidgetSpec) {
    return null
  }
  return generateWidgetProps(
    props.editWidgetSpec.general_settings.title || { text: '', render_mode: 'hidden' },
    props.editWidgetSpec.content as WidgetContentType,
    props.editWidgetSpec.filter_context.filters as ConfiguredFilters
  )
})

const filterDefinitions = useFilterDefinitions()
const widgetFilterManager = useWidgetFilterManager(
  props.editWidgetSpec?.filter_context.filters || {},
  filterDefinitions
)

// Stage 1
const hostFilterType = ref<ElementSelection>(
  editWidget.value?.effective_filter_context.restricted_to_single?.includes('host')
    ? ElementSelection.SPECIFIC
    : ElementSelection.MULTIPLE
)
const inventoryPath = ref<string | null>(null)
if (
  props.editWidgetSpec &&
  (props.editWidgetSpec.content as InventoryContent).type === 'inventory'
) {
  inventoryPath.value = (props.editWidgetSpec.content as InventoryContent).path
}

const wizardHandler = useWizard(2)

const wizardStages: QuickSetupStageSpec[] = [
  {
    title: _t('Data selection'),
    actions: [],
    errors: []
  },
  {
    title: _t('Visualization'),
    actions: [],
    errors: []
  }
]

const contextConfiguredFilters = computed((): ConfiguredFilters => {
  return parseContextConfiguredFilters(props.contextFilters)
})

const recapAndNext = () => {
  if (!inventoryPath.value) {
    wizardStages[0]!.errors = [_t('Please select a HW/SW inventory property.')]
    return
  }
  wizardStages[0]!.errors = []

  widgetFilterManager.closeSelectionMenu()
  wizardStages[0]!.recapContent = h(FiltersRecap, {
    contextConfiguredFilters: contextConfiguredFilters.value,
    widgetFilters: widgetFilterManager.getConfiguredFilters()
  })
  wizardHandler.next()
}

const appliedFilters = computed((): ConfiguredFilters => {
  return squashFilters(contextConfiguredFilters.value, widgetFilterManager.getConfiguredFilters())
})

const handleAddWidget = (
  content: WidgetContent,
  generalSettings: WidgetGeneralSettings,
  widgetFilters: ConfiguredFilters
) => {
  const filterContext = {
    uses_infos: ['host'],
    filters: widgetFilters,
    restricted_to_single: hostFilterType.value === ElementSelection.SPECIFIC ? ['host'] : []
  } as WidgetFilterContext

  emit('addWidget', content, generalSettings, filterContext)
}
</script>

<template>
  <WizardContainer>
    <WizardStepsContainer v-if="widgetFilterManager.selectionMenuOpen.value">
      <AddFilters
        v-model:filters="widgetFilterManager.filterHandler"
        :filter-selection-target="widgetFilterManager.selectionMenuCurrentTarget.value"
        :close="widgetFilterManager.closeSelectionMenu"
      />
    </WizardStepsContainer>

    <WizardStepsContainer v-else>
      <StepsHeader
        :title="_t('HW/SW Inventory')"
        :subtitle="_t('Define widget')"
        @back="() => emit('goBack')"
      />

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

    <WizardStageContainer>
      <CloseButton @close="() => emit('goBack')" />
      <Stage1
        v-if="wizardHandler.stage.value === 0"
        v-model:host-filter-type="hostFilterType"
        v-model:inventory-path="inventoryPath"
        :context-filters="contextFilters"
        :inventory-paths="inventoryPaths"
        :widget-configured-filters="widgetFilterManager.getConfiguredFilters()"
        :widget-active-filters="widgetFilterManager.getSelectedFilters()"
        :is-in-filter-selection-menu-focus="widgetFilterManager.objectTypeIsInFocus"
        @go-next="recapAndNext"
        @set-focus="(objectType) => widgetFilterManager.openSelectionMenu(objectType)"
        @update-filter-values="
          (filterId, values) => widgetFilterManager.updateFilterValues(filterId, values)
        "
        @reset-object-type-filters="
          (objectType) => widgetFilterManager.resetFilterValuesOfObjectType(objectType)
        "
        @remove-filter="(filterId) => widgetFilterManager.filterHandler.removeFilter(filterId)"
      />
      <Suspense>
        <Stage2
          v-if="wizardHandler.stage.value === 1"
          :dashboard-key="dashboardKey"
          :filters="appliedFilters"
          :widget-filters="widgetFilterManager.getConfiguredFilters()"
          :edit-widget="editWidget"
          :dashboard-constants="dashboardConstants"
          :inventory-path="inventoryPath"
          @go-prev="wizardHandler.prev"
          @add-widget="handleAddWidget"
        />

        <template #fallback>
          <div>{{ _t('Loading widget visualization settings...') }}</div>
        </template>
      </Suspense>
    </WizardStageContainer>
  </WizardContainer>
</template>
