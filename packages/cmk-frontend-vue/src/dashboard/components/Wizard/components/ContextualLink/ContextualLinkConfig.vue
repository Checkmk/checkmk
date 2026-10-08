<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="C extends LinkedContent">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import CmkIndent from 'cmk-ui-library/components/CmkIndent.vue'
import { useFilterDefinitions } from 'cmk-ui-library/components/filter'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import CmkInlineValidation from 'cmk-ui-library/components/user-input/CmkInlineValidation.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

import ContextualLinkTargetPicker from './ContextualLinkTargetPicker.vue'
import type { ConfigurableMode, ContextFilterIdOf, LinkedContent } from './contextualLink'
import type { CustomLinkDraft, UseContextualLink } from './useContextualLink'

const { _t } = usei18n()

const handler = defineModel<UseContextualLink<C>>('handler', { required: true })
const { defaultTarget } = defineProps<{
  // The title of the page the widget's built-in link leads to, if it has a single one.
  defaultTarget?: TranslatedString
}>()

const filterDefinitions = useFilterDefinitions()

const MODE_TITLES = {
  default: _t('Default'),
  inherited: _t('Inherited'),
  custom: _t('Custom')
}

const modeOptions = computed(() =>
  handler.value.modes.map((mode) => ({ name: mode, title: MODE_TITLES[mode] }))
)

const selectedMode = computed<string | null>({
  get: () => handler.value.mode.value,
  set: (value) => {
    handler.value.mode.value = value as ConfigurableMode
  }
})

function filterTitle(filterId: string) {
  return untranslated(filterDefinitions[filterId]?.title ?? filterId)
}

function toggleFilter(
  link: CustomLinkDraft<ContextFilterIdOf<C>>,
  filterId: ContextFilterIdOf<C>,
  carried: boolean
) {
  link.filters = carried
    ? handler.value.filters.filter((f) => f === filterId || link.filters.includes(f))
    : link.filters.filter((f) => f !== filterId)
}
</script>

<template>
  <CmkCheckbox v-model="handler.enabled.value" :label="_t('Add contextual link')" />
  <CmkIndent v-if="handler.enabled.value">
    <CmkDropdown
      v-model="selectedMode"
      :label="_t('Mode')"
      :options="{ type: 'fixed', suggestions: modeOptions }"
    />

    <div v-if="handler.mode.value === 'default'" class="db-contextual-link-config__mode">
      <template v-if="defaultTarget !== undefined">
        <p>{{ _t('Target page') }}</p>
        <span class="db-contextual-link-config__target">
          <CmkIcon name="link" size="small" />
          {{ defaultTarget }}
        </span>
      </template>
      <p>{{ _t('Redirect to the default page defined by Checkmk.') }}</p>
    </div>

    <div v-if="handler.mode.value === 'inherited'" class="db-contextual-link-config__mode">
      <ContextualLinkTargetPicker
        v-model="handler.inheritedTarget.value"
        :single-infos="handler.singleInfos"
      />
      <CmkCheckbox
        v-model="handler.inheritedIncludeTimeRange.value"
        :label="_t('Include current time range')"
      />
      <p v-if="handler.inheritedIncludesContext">
        {{
          _t('Always included: the applied dashboard and widget filters, and the clicked element.')
        }}
      </p>
      <p v-else>{{ _t('Always included: the clicked element.') }}</p>
    </div>

    <div v-if="handler.mode.value === 'custom'" class="db-contextual-link-config__mode">
      <div
        v-for="(link, index) in handler.customLinks.value"
        :key="link.id"
        class="db-contextual-link-config__link"
      >
        <CmkInput v-model="link.title" :aria-label="_t('Title')" :placeholder="_t('Title')" />
        <ContextualLinkTargetPicker v-model="link.target" :single-infos="handler.singleInfos" />
        <CmkCheckbox
          v-for="filterId in handler.filters"
          :key="filterId"
          :model-value="link.filters.includes(filterId)"
          :label="filterTitle(filterId)"
          @update:model-value="(carried: boolean) => toggleFilter(link, filterId, carried)"
        />
        <CmkCheckbox
          v-model="link.includeContext"
          :label="_t('Include dashboard & widget filters')"
        />
        <CmkCheckbox v-model="link.includeTimeRange" :label="_t('Include current time range')" />
        <CmkButton @click="handler.removeCustomLink(index)">{{ _t('Remove link') }}</CmkButton>
      </div>
      <CmkButton @click="handler.addCustomLink()">{{ _t('Add link') }}</CmkButton>
    </div>

    <CmkInlineValidation
      v-if="handler.validationErrors.value.length > 0"
      :validation="handler.validationErrors.value"
    />
  </CmkIndent>
</template>

<style scoped>
.db-contextual-link-config__mode,
.db-contextual-link-config__link {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
  margin-top: var(--dimension-4);
}

.db-contextual-link-config__target {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
}

.db-contextual-link-config__link {
  padding-left: var(--dimension-4);
  border-left: 1px solid var(--ux-theme-6);
}
</style>
