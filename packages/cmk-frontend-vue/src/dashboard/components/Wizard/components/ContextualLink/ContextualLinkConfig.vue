<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="C extends LinkedContent">
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import CmkCollapsible, { CmkCollapsibleTitle } from 'cmk-ui-library/components/CmkCollapsible'
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown'
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import CmkIndent from 'cmk-ui-library/components/CmkIndent.vue'
import CmkMenu, { type CmkMenuCategory, type CmkMenuItem } from 'cmk-ui-library/components/CmkMenu'
import CmkToggleButtonGroup from 'cmk-ui-library/components/CmkToggleButtonGroup.vue'
import FormAutocompleter from 'cmk-ui-library/components/FormAutocompleter/FormAutocompleter.vue'
import {
  CmkRemoveFilterButton,
  getCategoryDefinition,
  useFilterDefinitions,
  useFilterGroups
} from 'cmk-ui-library/components/filter'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import CmkInlineButton from 'cmk-ui-library/components/user-input/CmkInlineButton.vue'
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
const filterGroups = useFilterGroups()

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

const filterMenuItems = computed<CmkMenuItem[]>(() =>
  handler.value.filters.map((filterId) => {
    const { info, group } = filterDefinitions[filterId]?.extensions ?? {}
    return {
      label: [{ text: filterTitle(filterId), truncateOrder: 1 }],
      value: filterId,
      category: info,
      detail: group ? (filterGroups[group]?.title ?? group) : undefined
    }
  })
)

// A toggle with a single object to pick would narrow nothing.
const filterCategories = computed<CmkMenuCategory[] | undefined>(() => {
  const infos = [...new Set(filterMenuItems.value.map(({ category }) => category))].filter(
    (info) => info !== undefined
  )
  return infos.length > 1
    ? infos.map((info) => ({ value: info, title: getCategoryDefinition(info).title }))
    : undefined
})

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
  <CmkIndent
    v-if="handler.enabled.value"
    class="db-contextual-link-config db-contextual-link-config__indent"
  >
    <CmkToggleButtonGroup
      v-model="selectedMode"
      :options="modeOptions"
      size="small"
      spacing="none"
    />

    <div v-if="handler.mode.value === 'default'" class="db-contextual-link-config__mode">
      <div v-if="defaultTarget !== undefined" class="db-contextual-link-config__field">
        <p>{{ _t('Target page') }}</p>
        <CmkIndent
          class="db-contextual-link-config__indent db-contextual-link-config__default-target"
        >
          <span class="db-contextual-link-config__target">
            <CmkMultitoneIcon name="chain" primary-color="font" size="small" aria-hidden="true" />
            <span class="db-contextual-link-config__target-title">{{ defaultTarget }}</span>
          </span>
          <p class="db-contextual-link-config__copy">
            {{ _t('Redirect to the default page defined by Checkmk.') }}
          </p>
        </CmkIndent>
      </div>
      <p v-else class="db-contextual-link-config__copy">
        {{ _t('Redirect to the default page defined by Checkmk.') }}
      </p>
    </div>

    <div v-if="handler.mode.value === 'inherited'" class="db-contextual-link-config__mode">
      <div class="db-contextual-link-config__field">
        <p>{{ _t('Target page') }}</p>
        <CmkIndent class="db-contextual-link-config__indent db-contextual-link-config__group">
          <div class="db-contextual-link-config__field">
            <ContextualLinkTargetPicker v-model="handler.inheritedTarget.value" />
            <CmkCheckbox
              v-model="handler.inheritedIncludeTimeRange.value"
              :label="_t('Include current time range')"
            />
            <CmkCheckbox
              v-model="handler.inheritedIncludeContext.value"
              :label="_t('Include dashboard & widget filters')"
            />
          </div>
          <div class="db-contextual-link-config__field">
            <p>{{ _t('Always included in the contextual link') }}</p>
            <ul class="db-contextual-link-config__included">
              <li>{{ _t('Contextual filter = clicked element') }}</li>
            </ul>
          </div>
        </CmkIndent>
      </div>
    </div>

    <div
      v-if="handler.mode.value === 'custom'"
      class="db-contextual-link-config__mode db-contextual-link-config__links"
    >
      <div v-for="(link, index) in handler.customLinks.value" :key="link.id">
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
          <CmkIndent
            class="db-contextual-link-config__indent db-contextual-link-config__group db-contextual-link-config__link-body"
          >
            <div class="db-contextual-link-config__field">
              <p>{{ _t('Link name') }}</p>
              <CmkInput
                v-model="link.title"
                :aria-label="_t('Link name')"
                :placeholder="_t('e.g. host details')"
              />
            </div>
            <div class="db-contextual-link-config__field">
              <p>{{ _t('Target page') }}</p>
              <ContextualLinkTargetPicker v-model="link.target" />
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
              <CmkIndent
                v-if="link.includeClickedElement"
                class="db-contextual-link-config__indent db-contextual-link-config__field"
              >
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
                <div class="db-contextual-link-config__add-filter">
                  <CmkMenu
                    :items="filterMenuItems"
                    :categories="filterCategories"
                    :label="_t('Add filter')"
                    trigger-icon="plus"
                    :trigger-text="_t('Add filter')"
                    :search-placeholder="_t('Search filters ...')"
                    searchable
                    @select="(filterId: string) => handler.addFilter(link, filterId)"
                  />
                </div>
              </CmkIndent>
            </div>
          </CmkIndent>
        </CmkCollapsible>
      </div>
      <CmkInlineButton class="db-contextual-link-config__add-link" @click="handler.addCustomLink()">
        {{ _t('Add contextual link') }}
      </CmkInlineButton>
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
/* The gaps alone space the indents, so that an indent's line spans just its content. Doubled
   for the specificity over the indent's own spacing. */
.db-contextual-link-config__indent.db-contextual-link-config__indent {
  margin-top: 0;
  margin-bottom: 0;
  padding-top: 0;
  padding-bottom: 0;
}

.db-contextual-link-config.db-contextual-link-config__indent {
  margin-top: var(--dimension-4);
}

.db-contextual-link-config__mode {
  display: flex;
  flex-direction: column;
  margin-top: var(--dimension-5);
}

.db-contextual-link-config__group {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-5);
}

.db-contextual-link-config__field {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);

  > p {
    margin: 0;
  }
}

.db-contextual-link-config__links {
  gap: var(--dimension-7);
}

.db-contextual-link-config__link-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--dimension-4);
}

.db-contextual-link-config__link-body.db-contextual-link-config__indent {
  margin-top: var(--dimension-6);
}

.db-contextual-link-config__filter {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
}

/* Buttons hug their content instead of stretching across the column. */
.db-contextual-link-config__add-filter,
.db-contextual-link-config__add-link {
  align-self: flex-start;
}

.db-contextual-link-config__default-target {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-7);
}

.db-contextual-link-config__target {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
}

/* The look of a link, without leading anywhere: the page depends on the clicked element. */
.db-contextual-link-config__target-title {
  font-weight: var(--font-weight-semibold);

  &:hover {
    text-decoration: underline;
  }
}

.db-contextual-link-config__copy {
  margin: 0;
  color: var(--font-color-secondary);
}

.db-contextual-link-config__included {
  margin: 0;
  padding-left: var(--dimension-6);
}
</style>
