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
import CmkTag from 'cmk-ui-library/components/CmkTag.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import type { GlobalSettingsScope } from '../api'
import { isModified, isSiteOverride } from '../lib/origin'
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
      <CmkTag
        v-if="modifiedCount > 0"
        size="medium"
        variant="fill"
        class="global-settings-topic__count"
        :content="modifiedCountLabel"
        :title="modifiedCountLabel"
      />
      <CmkTag
        v-if="siteOverrideCount > 0"
        size="medium"
        variant="fill"
        class="global-settings-topic__count"
        :content="siteOverrideCountLabel"
        :title="siteOverrideCountLabel"
      />
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

.global-settings-topic__count {
  min-width: 90px;
  text-align: center;
}
</style>
