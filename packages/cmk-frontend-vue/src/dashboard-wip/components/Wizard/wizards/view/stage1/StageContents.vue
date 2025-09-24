<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import ToggleButtonGroup from '@/components/ToggleButtonGroup.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

import ActionBar from '@/dashboard-wip/components/Wizard/components/ActionBar.vue'
import ActionButton from '@/dashboard-wip/components/Wizard/components/ActionButton.vue'
import ContentSpacer from '@/dashboard-wip/components/Wizard/components/ContentSpacer.vue'
import NewView from '@/dashboard-wip/components/Wizard/wizards/view/stage1/components/NewView.vue'
import ReferenceView from '@/dashboard-wip/components/Wizard/wizards/view/stage1/components/ReferenceView.vue'
import type { Filters } from '@/dashboard-wip/components/filter/composables/useFilters'
import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'

import { ViewSelectionMode } from '../types'
import type {
  CopyExistingViewSelection,
  LinkExistingViewSelection,
  NewViewSelection,
  ViewSelection
} from '../types'

const { _t } = usei18n()

interface Stage1Props {
  dashboardFilters: ConfiguredFilters
  quickFilters: ConfiguredFilters
  filters: Filters
  // TODO: a read only mode is probably required here
}

defineProps<Stage1Props>()

const emit = defineEmits<{
  goNext: [selectedView: ViewSelection]
}>()

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
  </div>
</template>
