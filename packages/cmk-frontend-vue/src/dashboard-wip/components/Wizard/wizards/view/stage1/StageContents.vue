<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'

import usei18n from '@/lib/i18n'

import ToggleButtonGroup from '@/components/ToggleButtonGroup.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

import ActionBar from '@/dashboard-wip/components/Wizard/components/ActionBar.vue'
import ActionButton from '@/dashboard-wip/components/Wizard/components/ActionButton.vue'
import ContentSpacer from '@/dashboard-wip/components/Wizard/components/ContentSpacer.vue'
import WidgetObjectFilterConfiguration from '@/dashboard-wip/components/Wizard/components/filter/WidgetObjectFilterConfiguration/WidgetObjectFilterConfiguration.vue'
import { parseFilters } from '@/dashboard-wip/components/Wizard/components/filter/utils.ts'
import { ElementSelection } from '@/dashboard-wip/components/Wizard/types.ts'
import NewView from '@/dashboard-wip/components/Wizard/wizards/view/stage1/components/NewView.vue'
import ReferenceView from '@/dashboard-wip/components/Wizard/wizards/view/stage1/components/ReferenceView.vue'
import type {
  ConfiguredFilters,
  ConfiguredValues
} from '@/dashboard-wip/components/filter/types.ts'
import { useFilterDefinitions } from '@/dashboard-wip/components/filter/utils.ts'
import { useVisualInfoCollection } from '@/dashboard-wip/composables/api/useVisualInfoCollection.ts'
import type { ContextFilters } from '@/dashboard-wip/types/filter.ts'
import type { ObjectType } from '@/dashboard-wip/types/shared.ts'

import { ViewSelectionMode } from '../types'
import type {
  CopyExistingViewSelection,
  LinkExistingViewSelection,
  NewViewSelection,
  ViewSelection
} from '../types'

const { _t } = usei18n()

interface Stage1Props {
  widgetConfiguredFilters: ConfiguredFilters
  widgetActiveFilters: string[]
  contextFilters: ContextFilters
  currentFilterSelectionMenuFocus: ObjectType | null
  // TODO: a read only mode is probably required here
}

const props = defineProps<Stage1Props>()

const emit = defineEmits<{
  (e: 'set-focus', target: ObjectType): void
  (e: 'update-filter-values', filterId: string, values: ConfiguredValues): void
  (e: 'reset-object-type-filters', objectType: ObjectType): void
  (e: 'reset-all-filters'): void
  (e: 'goNext', selectedView: ViewSelection): void
}>()

const { byId, ensureLoaded } = useVisualInfoCollection()
const filterDefinitions = useFilterDefinitions()

const selectedDatasource = defineModel<string | null>('selectedDatasource', { default: '' })
const contextInfos = defineModel<string[]>('contextInfos', { default: [] })
const restrictedToSingleInfos = defineModel<string[]>('restrictedToSingleInfos', { default: [] })
const originalViewName = defineModel<string | null>('originalViewName', { default: null })
const referencedViewName = defineModel<string | null>('referencedViewName', { default: null })

function goToNextStage() {
  let viewSelection: ViewSelection
  if (modeSelection.value === ViewSelectionMode.NEW) {
    viewSelection = {
      type: ViewSelectionMode.NEW,
      datasource: selectedDatasource.value,
      restrictedToSingle: restrictedToSingleInfos.value
    } as NewViewSelection
  } else if (modeSelection.value === ViewSelectionMode.COPY) {
    if (!originalViewName.value) {
      throw new Error('No original view name selected')
    }
    viewSelection = {
      type: ViewSelectionMode.COPY,
      viewName: originalViewName.value
    } as CopyExistingViewSelection
  } else if (modeSelection.value === ViewSelectionMode.LINK) {
    if (!referencedViewName.value) {
      throw new Error('No referenced view name selected')
    }
    viewSelection = {
      type: ViewSelectionMode.LINK,
      viewName: referencedViewName.value
    } as LinkExistingViewSelection
  } else {
    throw new Error('Invalid mode selection')
  }
  emit('goNext', viewSelection)
}

const modeSelection = defineModel<ViewSelectionMode>('modeSelection', {
  default: ViewSelectionMode.NEW
})

onMounted(async () => {
  await ensureLoaded()
})

watch(contextInfos, () => {
  emit('reset-all-filters')
})

watch(restrictedToSingleInfos, (newList, oldList) => {
  const oldSet = new Set(oldList)
  const newSet = new Set(newList)

  const symmetricDifference = new Set<ObjectType>()
  for (const v of oldSet) {
    if (!newSet.has(v)) {
      symmetricDifference.add(v)
    }
  }
  for (const v of newSet) {
    if (!oldSet.has(v)) {
      symmetricDifference.add(v)
    }
  }

  if (symmetricDifference) {
    for (const objectType of symmetricDifference) {
      emit('reset-object-type-filters', objectType)
    }
  }
})

const getVisual = (objectType: ObjectType) => {
  return byId.value[objectType]
}

const configuredFiltersByObjectType = computed(() => {
  return parseFilters(
    props.widgetConfiguredFilters,
    props.widgetActiveFilters,
    filterDefinitions,
    new Set(contextInfos.value)
  )
})

const sortedContextInfos = computed(() => {
  // Preserve original order unless both 'host' and 'service' are present
  // and 'service' appears before 'host'. In that case, move 'host'
  // directly before 'service' to keep it consistent with other widget workflows
  const infos = [...contextInfos.value]
  const hostIndex = infos.indexOf('host')
  const serviceIndex = infos.indexOf('service')

  if (hostIndex !== -1 && serviceIndex !== -1 && hostIndex > serviceIndex) {
    infos.splice(hostIndex, 1)
    const newServiceIndex = infos.indexOf('service')
    infos.splice(newServiceIndex, 0, 'host')
  }

  return infos
})
</script>

<template>
  <div>
    <CmkHeading type="h1">
      {{ _t('Data selection') }}
    </CmkHeading>

    <ContentSpacer />

    <ActionBar align-items="left">
      <ActionButton
        :label="_t('Next step: Data configuration')"
        :icon="{ name: 'continue', side: 'right' }"
        :action="goToNextStage"
        variant="secondary"
      />
    </ActionBar>

    <ContentSpacer />

    <CmkParagraph>
      {{ _t('Select the data you want to analyze') }} <br />
      {{ _t("Dashboard filters apply here and don't have to be selected again") }}
    </CmkParagraph>

    <ContentSpacer />
    <CmkHeading type="h2">
      {{ _t('View selection') }}
    </CmkHeading>
    <ContentSpacer />
    <ToggleButtonGroup
      v-model="modeSelection"
      :options="[
        { label: _t('New view'), value: ViewSelectionMode.NEW },
        {
          label: _t('Copy view'),
          value: ViewSelectionMode.COPY
        },
        {
          label: _t('Link to existing view'),
          value: ViewSelectionMode.LINK
        }
      ]"
    />
    <div v-if="modeSelection === ViewSelectionMode.NEW">
      <NewView
        v-model:selected-datasource="selectedDatasource"
        v-model:context-infos="contextInfos"
        v-model:restricted-to-single-infos="restrictedToSingleInfos"
      />
    </div>
    <div v-else-if="modeSelection === ViewSelectionMode.COPY">
      <ReferenceView
        v-model:referenced-view="originalViewName"
        v-model:context-infos="contextInfos"
      />
    </div>
    <div v-else-if="modeSelection === ViewSelectionMode.LINK">
      <ReferenceView
        v-model:referenced-view="referencedViewName"
        v-model:context-infos="contextInfos"
      />
    </div>
    <ContentSpacer />
    <div v-for="objectType in sortedContextInfos" :key="objectType">
      <h2>
        {{
          getVisual(objectType)?.title || _t('Unknown object type: %{objectType}', { objectType })
        }}
      </h2>
      <WidgetObjectFilterConfiguration
        :object-type="objectType"
        :object-selection-mode="
          restrictedToSingleInfos.includes(objectType)
            ? ElementSelection.SPECIFIC
            : ElementSelection.MULTIPLE
        "
        :object-configured-filters="configuredFiltersByObjectType[objectType]!"
        :in-focus="currentFilterSelectionMenuFocus === objectType"
        :context-filters="contextFilters"
        :show-context-filters-section="objectType in ['host', 'service']"
        @set-focus="emit('set-focus', $event)"
        @update-filter-values="(filterId, values) => emit('update-filter-values', filterId, values)"
      />
      <ContentSpacer :height="10" />
    </div>
  </div>
</template>
<style scoped>
h2 {
  font-size: var(--font-size-large);
}
</style>
