<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="C extends LinkedContent">
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkCollapsible, { CmkCollapsibleTitle } from 'cmk-ui-library/components/CmkCollapsible'
import CmkDropdown, { CmkAddDropdown } from 'cmk-ui-library/components/CmkDropdown'
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import CmkIndent from 'cmk-ui-library/components/CmkIndent.vue'
import CmkToggleButtonGroup from 'cmk-ui-library/components/CmkToggleButtonGroup.vue'
import FormAutocompleter from 'cmk-ui-library/components/FormAutocompleter/FormAutocompleter.vue'
import { CmkRemoveFilterButton, useFilterDefinitions } from 'cmk-ui-library/components/filter'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import CmkInlineValidation from 'cmk-ui-library/components/user-input/CmkInlineValidation.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed, ref } from 'vue'

import ContextualLinkTargetPicker from './ContextualLinkTargetPicker.vue'
import DeleteContextualLinkPopup from './DeleteContextualLinkPopup.vue'
import type { ConfigurableMode, FilterKeyOption, LinkedContent } from './contextualLink'
import type { UseContextualLink } from './useContextualLink'

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
  handler.value.modes.map((mode) => ({ value: mode, label: MODE_TITLES[mode] }))
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

const filterOptions = computed(() =>
  handler.value.filters.map((filterId) => ({ name: filterId, title: filterTitle(filterId) }))
)

const KEY_LABELS: Record<FilterKeyOption['type'], TranslatedString> = {
  label: _t('Label key'),
  tag_group: _t('Tag group'),
  aux_tag: _t('Auxiliary tag')
}

function keyAutocompleter(key: FilterKeyOption): Autocompleter {
  switch (key.type) {
    case 'label':
      return {
        fetch_method: 'rest_autocomplete',
        data: { ident: 'label_key', params: { object_type: key.object_type } }
      }
    case 'tag_group':
      return {
        fetch_method: 'rest_autocomplete',
        data: { ident: 'tag_groups', params: { strict: true, escape_regex: false } }
      }
    case 'aux_tag':
      return {
        fetch_method: 'rest_autocomplete',
        data: { ident: 'aux_tags', params: { strict: true } }
      }
  }
}

const closedLinks = ref(new Set<number>())

function toggleLink(id: number) {
  if (closedLinks.value.has(id)) {
    closedLinks.value.delete(id)
  } else {
    closedLinks.value.add(id)
  }
}

const pendingDelete = ref<number | null>(null)

function confirmDelete() {
  if (pendingDelete.value !== null) {
    handler.value.removeCustomLink(pendingDelete.value)
  }
  pendingDelete.value = null
}
</script>

<template>
  <CmkCheckbox v-model="handler.enabled.value" :label="_t('Add contextual link')" />
  <CmkIndent v-if="handler.enabled.value">
    <CmkToggleButtonGroup v-model="selectedMode" :options="modeOptions" />

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
      <p>{{ _t('Target page') }}</p>
      <ContextualLinkTargetPicker
        v-model="handler.inheritedTarget.value"
        :single-infos="handler.singleInfos"
      />
      <CmkCheckbox
        v-model="handler.inheritedIncludeTimeRange.value"
        :label="_t('Include current time range')"
      />
      <div>
        <p>{{ _t('Always included in the contextual link:') }}</p>
        <ul class="db-contextual-link-config__included">
          <li v-if="handler.inheritedIncludesContext">
            {{ _t('Applied dashboard & widget filters') }}
          </li>
          <li>{{ _t('Contextual filter = clicked element') }}</li>
        </ul>
      </div>
    </div>

    <div v-if="handler.mode.value === 'custom'" class="db-contextual-link-config__mode">
      <div
        v-for="(link, index) in handler.customLinks.value"
        :key="link.id"
        class="db-contextual-link-config__link"
      >
        <div class="db-contextual-link-config__link-header">
          <CmkCollapsibleTitle
            :title="_t('Link %{n}', { n: index + 1 })"
            :open="!closedLinks.has(link.id)"
            @toggle-open="toggleLink(link.id)"
          />
          <CmkIconButton
            name="delete"
            :title="_t('Delete contextual link')"
            @click="pendingDelete = index"
          />
        </div>
        <CmkCollapsible :open="!closedLinks.has(link.id)">
          <div class="db-contextual-link-config__link-body">
            <p>{{ _t('Link name') }}</p>
            <CmkInput
              v-model="link.title"
              :aria-label="_t('Link name')"
              :placeholder="_t('e.g. host details')"
            />
            <p>{{ _t('Target page') }}</p>
            <ContextualLinkTargetPicker v-model="link.target" :single-infos="handler.singleInfos" />
            <CmkCheckbox
              v-model="link.includeTimeRange"
              :label="_t('Include current time range')"
            />
            <CmkCheckbox
              v-model="link.includeContext"
              :label="_t('Include dashboard & widget filters')"
            />
            <CmkCheckbox
              v-model="link.includeClickedElement"
              :label="_t('Include filter context of clicked element')"
            />
            <CmkIndent v-if="link.includeClickedElement">
              <div
                v-for="(filter, filterIndex) in link.filters"
                :key="filter.id"
                class="db-contextual-link-config__filter"
              >
                <CmkDropdown
                  :model-value="filter.filterId"
                  :label="_t('Filter')"
                  :options="{ type: 'filtered', suggestions: filterOptions }"
                  @update:model-value="
                    (filterId: string | null) => handler.setFilter(filter, filterId)
                  "
                />
                <FormAutocompleter
                  v-if="filter.keyOption !== undefined"
                  v-model="filter.key"
                  :placeholder="KEY_LABELS[filter.keyOption.type]"
                  :label="KEY_LABELS[filter.keyOption.type]"
                  :autocompleter="keyAutocompleter(filter.keyOption)"
                />
                <CmkRemoveFilterButton
                  :filter-name="filterTitle(filter.filterId)"
                  @remove="link.filters.splice(filterIndex, 1)"
                />
              </div>
              <CmkAddDropdown
                :options="{ type: 'filtered', suggestions: filterOptions }"
                :label="_t('Add filter')"
                @select="(filterId: string) => handler.addFilter(link, filterId)"
              />
            </CmkIndent>
          </div>
        </CmkCollapsible>
      </div>
      <CmkButton :icon="{ name: 'plus' }" @click="handler.addCustomLink()">
        {{ _t('Add contextual link') }}
      </CmkButton>
      <DeleteContextualLinkPopup
        :open="pendingDelete !== null"
        @confirm="confirmDelete"
        @close="pendingDelete = null"
      />
    </div>

    <CmkInlineValidation
      v-if="handler.validationErrors.value.length > 0"
      :validation="handler.validationErrors.value"
    />
  </CmkIndent>
</template>

<style scoped>
.db-contextual-link-config__mode,
.db-contextual-link-config__link,
.db-contextual-link-config__link-body {
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

.db-contextual-link-config__included {
  margin: var(--dimension-3) 0 0;
  padding-left: var(--dimension-6);
}

.db-contextual-link-config__link {
  padding-left: var(--dimension-4);
  border-left: 1px solid var(--ux-theme-6);
}

.db-contextual-link-config__link-header,
.db-contextual-link-config__filter {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
}

.db-contextual-link-config__link-header {
  justify-content: space-between;
}

.db-contextual-link-config__filter + .db-contextual-link-config__filter {
  margin-top: var(--dimension-4);
}
</style>
