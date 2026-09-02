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
import CmkTag from 'cmk-ui-library/components/CmkTag.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import GlobalSettingsVariableRow from './GlobalSettingsVariableRow.vue'

const { _t, _tn } = usei18n()

const props = defineProps<{ topic: GlobalSettingsTopic; value: string }>()

const emit = defineEmits<{ edit: [variable: GlobalSettingsVariable] }>()

const modifiedCount = computed(
  () => props.topic.variables.filter((variable) => variable.modified).length
)
const variableCountLabel = computed(() =>
  _tn('%{count} variable', '%{count} variables', props.topic.variables.length, {
    count: props.topic.variables.length
  })
)
const modifiedCountLabel = computed(() => _t('%{count} modified', { count: modifiedCount.value }))
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
        size="medium"
        variant="fill"
        class="global-settings-topic__count"
        :content="variableCountLabel"
        :title="variableCountLabel"
      />
      <CmkTag
        size="medium"
        variant="fill"
        class="global-settings-topic__count"
        :content="modifiedCountLabel"
        :title="modifiedCountLabel"
      />
      <CmkButton
        size="small"
        :icon="{ name: 'reset', size: 'small' }"
        :title="_t('Reset all settings in this category to their factory defaults')"
        :disabled="modifiedCount === 0"
      >
        {{ _t('Reset') }}
      </CmkButton>
    </template>
    <template #content>
      <CmkAlertBox v-if="topic.warning !== null" variant="warning" size="small">
        {{ topic.warning }}
      </CmkAlertBox>
      <GlobalSettingsVariableRow
        v-for="variable in topic.variables"
        :key="variable.name"
        :variable="variable"
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
