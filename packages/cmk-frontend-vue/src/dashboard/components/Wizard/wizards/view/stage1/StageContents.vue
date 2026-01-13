<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import usei18n, { untranslated } from '@/lib/i18n'

import CmkAlertBox from '@/components/CmkAlertBox.vue'
import CmkToggleButtonGroup from '@/components/CmkToggleButtonGroup.vue'

import ContentSpacer from '@/dashboard/components/Wizard/components/ContentSpacer.vue'
import WidgetObjectFilterConfiguration from '@/dashboard/components/Wizard/components/filter/WidgetObjectFilterConfiguration/WidgetObjectFilterConfiguration.vue'
import { parseFilters } from '@/dashboard/components/Wizard/components/filter/utils.ts'
import { ElementSelection } from '@/dashboard/components/Wizard/types.ts'
import type { ConfiguredFilters, ConfiguredValues } from '@/dashboard/components/filter/types.ts'
import { useFilterDefinitions } from '@/dashboard/components/filter/utils.ts'
import { useInjectVisualInfos } from '@/dashboard/composables/useProvideVisualInfos'
import type { DataSourceModel } from '@/dashboard/types/api'
import type { ContextFilters } from '@/dashboard/types/filter.ts'
import type { ObjectType } from '@/dashboard/types/shared.ts'
import type { EmbeddedViewContent, LinkedViewContent } from '@/dashboard/types/widget'

import SectionBlock from '../../../components/SectionBlock.vue'
import Stage1Header from '../../../components/Stage1Header.vue'
import type {
  CopyExistingViewSelection,
  LinkExistingViewSelection,
  NewViewSelection,
  ViewSelection
} from '../types'
import { ViewSelectionMode } from '../types'
import EditModeViewInfo from './components/EditModeViewInfo.vue'
import NewView from './components/NewView.vue'
import ReferenceView from './components/ReferenceView.vue'

const { _t } = usei18n()

interface Stage1Props {
  widgetConfiguredFilters: ConfiguredFilters
  widgetActiveFilters: string[]
  contextFilters: ContextFilters
  currentFilterSelectionMenuFocus: ObjectType | null
  isEditMode?: boolean
  content?: EmbeddedViewContent | LinkedViewContent | undefined
  datasourcesById: Record<string, DataSourceModel>
}

const props = defineProps<Stage1Props>()

const emit = defineEmits<{
  (e: 'set-focus', target: ObjectType): void
  (e: 'update-filter-values', filterId: string, values: ConfiguredValues): void
  (e: 'reset-object-type-filters', objectType: ObjectType): void
  (e: 'reset-all-filters'): void
  (e: 'remove-filter', filterId: string): void
  (e: 'goNext', selectedView: ViewSelection): void
  (e: 'overwrite-filters', filters: ConfiguredFilters): void
}>()

const visualInfosById = useInjectVisualInfos()
const filterDefinitions = useFilterDefinitions()

const selectedDatasource = defineModel<string | null>('selectedDatasource', { default: '' })
const contextInfos = defineModel<string[]>('contextInfos', { default: [] })
const restrictedToSingleInfos = defineModel<string[]>('restrictedToSingleInfos', { default: [] })
const originalViewName = defineModel<string | null>('originalViewName', { default: null })
const referencedViewName = defineModel<string | null>('referencedViewName', { default: null })
const modeSelection = defineModel<ViewSelectionMode>('modeSelection', {
  default: ViewSelectionMode.NEW
})

const error = ref<string | null>(null)

function goToNextStage() {
  error.value = null

  if (props.isEditMode) {
    emit('goNext', { type: 'edit' } as unknown as ViewSelection)
    return
  }

  let viewSelection: ViewSelection
  const mode = modeSelection.value

  if (mode === ViewSelectionMode.NEW) {
    if (!selectedDatasource.value) {
      error.value = _t('You must select a data source.')
      return
    }

    viewSelection = {
      type: ViewSelectionMode.NEW,
      datasource: selectedDatasource.value,
      restrictedToSingle: restrictedToSingleInfos.value
    } as NewViewSelection
  } else if (mode === ViewSelectionMode.COPY) {
    if (!originalViewName.value) {
      error.value = _t('You must select a view.')
      return
    }

    viewSelection = {
      type: ViewSelectionMode.COPY,
      viewName: originalViewName.value
    } as CopyExistingViewSelection
  } else if (mode === ViewSelectionMode.LINK) {
    if (!referencedViewName.value) {
      error.value = _t('You must select a view.')
      return
    }

    viewSelection = {
      type: ViewSelectionMode.LINK,
      viewName: referencedViewName.value
    } as LinkExistingViewSelection
  } else {
    throw new Error(`Unknown view selection mode: ${mode}`)
  }
  emit('goNext', viewSelection)
}

watch(modeSelection, () => {
  error.value = null
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
  return visualInfosById.value[objectType]
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
    <Stage1Header :button-title="_t('Next step: Data configuration')" @click="goToNextStage" />

    <SectionBlock :title="_t('View selection')">
      <template v-if="!isEditMode">
        <CmkToggleButtonGroup
          v-model="modeSelection as string"
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
        <CmkAlertBox v-if="error" variant="error" class="mb-5">
          {{ error }}
        </CmkAlertBox>
        <div v-if="modeSelection === ViewSelectionMode.NEW">
          <NewView
            v-model:selected-datasource="selectedDatasource"
            v-model:context-infos="contextInfos"
            v-model:restricted-to-single-infos="restrictedToSingleInfos"
            :datasources-by-id="datasourcesById"
          />
        </div>
        <div v-else-if="modeSelection === ViewSelectionMode.COPY">
          <ReferenceView
            v-model:referenced-view="originalViewName"
            v-model:context-infos="contextInfos"
            :datasources-by-id="datasourcesById"
            @overwrite-filters="(filters) => emit('overwrite-filters', filters)"
          />
        </div>
        <div v-else-if="modeSelection === ViewSelectionMode.LINK">
          <ReferenceView
            v-model:referenced-view="referencedViewName"
            v-model:context-infos="contextInfos"
            :datasources-by-id="datasourcesById"
            @overwrite-filters="(filters) => emit('overwrite-filters', filters)"
          />
        </div>
      </template>
      <EditModeViewInfo
        v-else
        :content="content!"
        :context-infos="contextInfos"
        :restricted-to-single-infos="restrictedToSingleInfos"
        :datasources-by-id="datasourcesById"
      />
      <ContentSpacer :dimension="8" />
      <div v-for="objectType in sortedContextInfos" :key="objectType">
        <SectionBlock
          :title="
            untranslated(
              getVisual(objectType)?.title ||
                _t('Unknown object type: %{objectType}', { objectType })
            )
          "
        >
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
            @update-filter-values="
              (filterId, values) => emit('update-filter-values', filterId, values)
            "
            @remove-filter="(filterId) => emit('remove-filter', filterId)"
          />
        </SectionBlock>
        <ContentSpacer :dimension="5" />
      </div>
    </SectionBlock>
  </div>
</template>
