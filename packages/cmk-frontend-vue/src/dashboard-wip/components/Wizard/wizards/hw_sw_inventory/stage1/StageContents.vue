<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

import type { ConfiguredFilters, ConfiguredValues } from '@/dashboard-wip/components/filter/types'
import type { ContextFilters } from '@/dashboard-wip/types/filter'
import type { ObjectType } from '@/dashboard-wip/types/shared'

import ActionBar from '../../../components/ActionBar.vue'
import ActionButton from '../../../components/ActionButton.vue'
import ContentSpacer from '../../../components/ContentSpacer.vue'
import SingleMultiWidgetObjectFilterConfiguration from '../../../components/filter/SingleMultiWidgetObjectFilterConfiguration.vue'
import type { ElementSelection } from '../../../types'

const { _t } = usei18n()

interface Stage1Props {
  contextFilters: ContextFilters
  widgetConfiguredFilters: ConfiguredFilters
  widgetActiveFilters: string[]
  isInFilterSelectionMenuFocus: (objectType: ObjectType) => boolean
}

const props = defineProps<Stage1Props>()
const emit = defineEmits<{
  (e: 'go-next'): void
  (e: 'set-focus', target: ObjectType): void
  (e: 'update-filter-values', filterId: string, values: ConfiguredValues): void
  (e: 'reset-object-type-filters', objectType: string): void
}>()

const gotoNextStage = () => {
  emit('go-next')
}

const hostFilterType = defineModel<ElementSelection>('hostFilterType', { required: true })
const hostObjectType = 'host'
</script>

<template>
  <CmkHeading type="h1">
    {{ _t('Data selection') }}
  </CmkHeading>

  <ContentSpacer />

  <ActionBar align-items="left">
    <ActionButton
      :label="_t('Next step: Visualization')"
      :icon="{ name: 'continue', side: 'right' }"
      :action="gotoNextStage"
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
    {{ _t('Host selection') }}
  </CmkHeading>
  <SingleMultiWidgetObjectFilterConfiguration
    v-model:mode-selection="hostFilterType"
    :object-type="hostObjectType"
    :configured-filters-of-object-type="props.widgetConfiguredFilters"
    :context-filters="contextFilters"
    :in-selection-menu-focus="isInFilterSelectionMenuFocus(hostObjectType)"
    @set-focus="emit('set-focus', $event)"
    @update-filter-values="(filterId, values) => emit('update-filter-values', filterId, values)"
    @reset-object-type-filters="emit('reset-object-type-filters', $event)"
  />
</template>
