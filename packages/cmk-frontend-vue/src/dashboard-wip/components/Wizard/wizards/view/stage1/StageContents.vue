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
import { ModeSelection } from '@/dashboard-wip/components/Wizard/wizards/view/types.ts'
import type { Filters } from '@/dashboard-wip/components/filter/composables/useFilters'
import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'

const { _t } = usei18n()

export interface CreateNewView {
  type: ModeSelection.NEW
  datasource: string
  restrictedToSingleInfos: string[]
}

export interface CopyExistingView {
  type: ModeSelection.COPY
  originalViewName: string
}

export interface LinkExistingView {
  type: ModeSelection.LINK
  viewName: string
}

type ViewCreationData = CreateNewView | CopyExistingView | LinkExistingView

interface Stage1Props {
  dashboardFilters: ConfiguredFilters
  quickFilters: ConfiguredFilters
  filters: Filters
  // TODO: a read only mode is probably required here
}

defineProps<Stage1Props>()

const emit = defineEmits<{
  goNext: [viewData: ViewCreationData]
}>()

const selectedDatasource = defineModel<string | null>('selectedDatasource', { default: '' })
const contextInfos = defineModel<string[]>('contextInfos', { default: [] })
const restrictedToSingleInfos = defineModel<string[]>('restrictedToSingleInfos', { default: [] })
const originalViewName = defineModel<string | null>('originalViewName', { default: null })
const referencedViewName = defineModel<string | null>('referencedViewName', { default: null })

function goToNextStage() {
  let viewData: ViewCreationData
  if (modeSelection.value === ModeSelection.NEW) {
    viewData = {
      type: ModeSelection.NEW,
      datasource: selectedDatasource.value,
      restrictedToSingleInfos: restrictedToSingleInfos.value
    } as CreateNewView
  } else if (modeSelection.value === ModeSelection.COPY) {
    if (!originalViewName.value) {
      throw new Error('No original view name selected')
    }
    viewData = {
      type: ModeSelection.COPY,
      originalViewName: originalViewName.value
    } as CopyExistingView
  } else if (modeSelection.value === ModeSelection.LINK) {
    if (!referencedViewName.value) {
      throw new Error('No referenced view name selected')
    }
    viewData = {
      type: ModeSelection.LINK,
      viewName: referencedViewName.value
    } as LinkExistingView
  } else {
    throw new Error('Invalid mode selection')
  }
  emit('goNext', viewData)
}

const modeSelection = defineModel<ModeSelection>('modeSelection', {
  default: ModeSelection.NEW
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
        { label: _t('New view'), value: ModeSelection.NEW },
        {
          label: _t('Copy view'),
          value: ModeSelection.COPY
        },
        {
          label: _t('Link to existing view'),
          value: ModeSelection.LINK
        }
      ]"
    />
    <div v-if="modeSelection === ModeSelection.NEW">
      <NewView
        v-model:selected-datasource="selectedDatasource"
        v-model:context-infos="contextInfos"
        v-model:restricted-to-single-infos="restrictedToSingleInfos"
      />
    </div>
    <div v-else-if="modeSelection === ModeSelection.COPY">
      <ReferenceView
        v-model:referenced-view="originalViewName"
        v-model:context-infos="contextInfos"
      />
    </div>
    <div v-else-if="modeSelection === ModeSelection.LINK">
      <ReferenceView
        v-model:referenced-view="referencedViewName"
        v-model:context-infos="contextInfos"
      />
    </div>
    <ContentSpacer />
  </div>
</template>
