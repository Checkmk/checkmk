<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type {
  GlobalSettingsTopic,
  GlobalSettingsVariable
} from 'cmk-shared-typing/typescript/global_settings'
import CmkAccordionItem from 'cmk-ui-library/components/CmkAccordion/CmkAccordionItem.vue'
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import type { GlobalSettingsScope } from '../api'
import { type ModificationFilter, isModified, isSiteOverride } from '../lib/origin'
import GlobalSettingsVariableRow from './GlobalSettingsVariableRow.vue'

const { _t } = usei18n()

const props = defineProps<{
  topic: GlobalSettingsTopic
  scope: GlobalSettingsScope
  value: string
  /** The variables to show, or null while no search narrows them. */
  match: ReadonlySet<string> | null
  query: string
}>()

const emit = defineEmits<{
  edit: [variable: GlobalSettingsVariable]
  filter: [filter: ModificationFilter]
}>()

// Only the variable array is filtered, so the header counts below stay totals.
const shownVariables = computed(() => {
  const match = props.match
  return match === null
    ? props.topic.variables
    : props.topic.variables.filter((variable) => match.has(variable.name))
})

const modifiedCount = computed(() => props.topic.variables.filter(isModified).length)
const siteOverrideCount = computed(
  () => props.topic.variables.filter((variable) => isSiteOverride(variable, props.scope)).length
)
const modifiedCountLabel = computed(() => _t('%{count} modified', { count: modifiedCount.value }))
const siteOverrideCountLabel = computed(() =>
  props.scope.type === 'site'
    ? _t('%{count} overridden on this site', { count: siteOverrideCount.value })
    : _t('%{count} overridden on sites', { count: siteOverrideCount.value })
)
const siteOverrideFilterLabel = computed(() =>
  props.scope.type === 'site'
    ? _t('Show only the settings this site overrides')
    : _t('Show only the settings the sites override')
)
</script>

<template>
  <CmkAccordionItem :value="value" :icon="topic.icon">
    <template #header>
      <div class="global-settings-topic__header">
        <span class="global-settings-topic__headline">{{ topic.headline }}</span>
        <span class="global-settings-topic__subline">{{ topic.subline }}</span>
      </div>
    </template>
    <template #header-right>
      <CmkButton
        v-if="modifiedCount > 0"
        size="small"
        variant="optional"
        class="global-settings-topic__filter"
        :title="_t('Show only the modified settings')"
        @click="emit('filter', 'modified')"
      >
        {{ modifiedCountLabel }}
      </CmkButton>
      <CmkButton
        v-if="siteOverrideCount > 0"
        size="small"
        variant="optional"
        class="global-settings-topic__filter"
        :title="siteOverrideFilterLabel"
        @click="emit('filter', 'site')"
      >
        {{ siteOverrideCountLabel }}
      </CmkButton>
    </template>
    <template #content>
      <CmkAlertBox v-if="topic.warning !== null" variant="warning" size="small">
        {{ topic.warning }}
      </CmkAlertBox>
      <GlobalSettingsVariableRow
        v-for="variable in shownVariables"
        :key="variable.name"
        :variable="variable"
        :query="query"
        @edit="emit('edit', variable)"
      />
    </template>
  </CmkAccordionItem>
</template>

<style scoped>
.global-settings-topic__header {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
}

.global-settings-topic__headline {
  color: var(--global-settings-topic-headline-color);
  font-size: var(--font-size-large);
  font-weight: var(--font-weight-bold);
}

.global-settings-topic__subline {
  color: var(--global-settings-topic-subline-color);
  font-size: var(--font-size-normal);
  font-weight: var(--font-weight-default);
}

.global-settings-topic__filter {
  min-width: 90px;
  font-size: var(--font-size-normal);
}
</style>
