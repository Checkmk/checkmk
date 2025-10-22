<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import CmkIndent from '@/components/CmkIndent.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

import ActionBar from '@/dashboard-wip/components/Wizard/components/ActionBar.vue'
import ActionButton from '@/dashboard-wip/components/Wizard/components/ActionButton.vue'
import ContentSpacer from '@/dashboard-wip/components/Wizard/components/ContentSpacer.vue'
import ObjectTypeFilterConfiguration from '@/dashboard-wip/components/Wizard/components/filter/ObjectTypeFilterConfiguration/ObjectTypeFilterConfiguration.vue'
import WidgetObjectFilterConfiguration from '@/dashboard-wip/components/Wizard/components/filter/WidgetObjectFilterConfiguration/WidgetObjectFilterConfiguration.vue'
import { parseFilters } from '@/dashboard-wip/components/Wizard/components/filter/utils.ts'
import { ElementSelection } from '@/dashboard-wip/components/Wizard/types'
import type { ConfiguredFilters, ConfiguredValues } from '@/dashboard-wip/components/filter/types'
import { useFilterDefinitions } from '@/dashboard-wip/components/filter/utils.ts'
import type { ContextFilters } from '@/dashboard-wip/types/filter.ts'
import type { ObjectType } from '@/dashboard-wip/types/shared.ts'

const { _t } = usei18n()

interface Stage1Props {
  widgetConfiguredFilters: ConfiguredFilters
  widgetActiveFilters: string[]
  contextFilters: ContextFilters
  isInFilterSelectionMenuFocus: (objectType: ObjectType) => boolean
}

interface Emits {
  (e: 'set-focus', target: ObjectType): void
  (e: 'update-filter-values', filterId: string, values: ConfiguredValues): void
  (e: 'goNext'): void
}

const props = defineProps<Stage1Props>()
const emit = defineEmits<Emits>()

const hostObjectType = 'host'
const eventObjectType = 'event'

// Filters
const filterDefinitions = useFilterDefinitions()
const configuredFiltersByObjectType = computed(() =>
  parseFilters(
    props.widgetConfiguredFilters,
    props.widgetActiveFilters,
    filterDefinitions,
    new Set(['host', 'event'])
  )
)
</script>

<template>
  <CmkHeading type="h1">
    {{ _t('Widget data') }}
  </CmkHeading>

  <ContentSpacer />

  <ActionBar align-items="left">
    <ActionButton
      :label="_t('Next step: Visualization')"
      :icon="{ name: 'continue', side: 'right' }"
      :action="() => emit('goNext')"
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

  <CmkIndent>
    <WidgetObjectFilterConfiguration
      :object-type="hostObjectType"
      :object-selection-mode="ElementSelection.MULTIPLE"
      :object-configured-filters="configuredFiltersByObjectType[hostObjectType] || {}"
      :in-focus="isInFilterSelectionMenuFocus(hostObjectType)"
      :context-filters="contextFilters"
      @set-focus="emit('set-focus', $event)"
      @update-filter-values="(filterId, values) => emit('update-filter-values', filterId, values)"
    />
  </CmkIndent>
  <ContentSpacer />

  <CmkHeading type="h2">
    {{ _t('Event selection') }}
  </CmkHeading>

  <CmkIndent>
    <ObjectTypeFilterConfiguration
      :object-type="eventObjectType"
      :object-selection-mode="ElementSelection.MULTIPLE"
      :object-configured-filters="configuredFiltersByObjectType[eventObjectType] || {}"
      :in-focus="isInFilterSelectionMenuFocus(eventObjectType)"
      :filter-labels="{
        title: _t('Widget filters'),
        tooltip: _t('Widget configured filters override dashboard and runtime filters')
      }"
      @set-focus="emit('set-focus', $event)"
      @update-filter-values="(filterId, values) => emit('update-filter-values', filterId, values)"
    />
  </CmkIndent>
  <ContentSpacer />
</template>
