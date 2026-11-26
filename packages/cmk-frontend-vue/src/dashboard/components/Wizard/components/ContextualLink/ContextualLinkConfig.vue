<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="C extends LinkedContent">
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import CmkCollapsible, { CmkCollapsibleTitle } from 'cmk-ui-library/components/CmkCollapsible'
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown'
import CmkHelpText from 'cmk-ui-library/components/CmkHelpText.vue'
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
import { computed, ref, watch } from 'vue'

import ContextualLinkTargetPicker from './ContextualLinkTargetPicker.vue'
import type {
  ConfigurableMode,
  FilterKeyOption,
  LinkedContent,
  VisualLocation
} from './contextualLink'
import type { UseContextualLink } from './useContextualLink'
import { linkTargetTitle, useLinkTargets } from './useLinkTargets'

const { _t } = usei18n()

const handler = defineModel<UseContextualLink<C>>('handler', { required: true })
const { defaultTarget, defaultCarries, unavailable } = defineProps<{
  // The title of the page the widget's built-in link leads to, if it has a single one.
  defaultTarget?: TranslatedString | undefined
  defaultCarries?: TranslatedString | undefined
  unavailable?: TranslatedString | undefined
}>()

const filterDefinitions = useFilterDefinitions()
const filterGroups = useFilterGroups()

type Choice = 'none' | ConfigurableMode

const CHOICE_TITLES: Record<Choice, TranslatedString> = {
  none: _t('None'),
  default: _t('Default'),
  inherited: _t('Inherited'),
  custom: _t('Custom')
}

const CHOICE_DESCRIPTIONS: Record<Choice, TranslatedString[]> = {
  none: [_t('This widget has no links to other pages.')],
  default: [_t("Opens Checkmk's default page for the clicked item.")],
  inherited: [_t('Opens one view or dashboard.'), _t('Always filtered by the clicked item.')],
  custom: [
    _t('Opens one or more views or dashboards.'),
    _t('Matching selected attributes of the clicked item.')
  ]
}

const choiceOptions = computed(() =>
  (unavailable ? ['none'] : ['none', ...handler.value.modes]).map((choice) => ({
    value: choice,
    label: CHOICE_TITLES[choice as Choice]
  }))
)

const selectedChoice = computed<string | null>({
  get: () => (handler.value.enabled.value && !unavailable ? handler.value.mode.value : 'none'),
  set: (value) => {
    if (unavailable) {
      return
    }
    if (value === 'none') {
      handler.value.enabled.value = false
      return
    }
    handler.value.enabled.value = true
    handler.value.mode.value = value as ConfigurableMode
  }
})

const choiceDescription = computed(() => {
  if (unavailable) {
    return [unavailable]
  }
  const choice = selectedChoice.value as Choice
  return choice === 'default'
    ? [...CHOICE_DESCRIPTIONS.default, ...(defaultCarries ? [defaultCarries] : [])]
    : CHOICE_DESCRIPTIONS[choice]
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

const { targets, viewsError, dashboardsError, load: loadTargets } = useLinkTargets()
watch(
  selectedChoice,
  (choice) => {
    if (choice === 'inherited' || choice === 'custom') {
      void loadTargets()
    }
  },
  { immediate: true }
)

const closedLinks = ref(new Set<number>())

// The heading is a flex box, which drops a plain leading space, hence the no-break space.
function collapsedSummary(target: VisualLocation | null): TranslatedString {
  return untranslated(
    `\u00a0· ${target === null ? _t('No target page yet') : linkTargetTitle(targets.value, target)}`
  )
}

function toggleLink(id: number) {
  if (closedLinks.value.has(id)) {
    closedLinks.value.delete(id)
  } else {
    closedLinks.value.add(id)
  }
}
</script>

<template>
  <div class="db-contextual-link-config">
    <CmkToggleButtonGroup
      v-model="selectedChoice"
      :options="choiceOptions"
      size="small"
      spacing="none"
    />
    <div class="db-contextual-link-config__choice-description">
      <p
        v-for="(line, index) in choiceDescription"
        :key="index"
        class="db-contextual-link-config__copy"
      >
        {{ line }}
      </p>
    </div>

    <div
      v-if="selectedChoice === 'default' && defaultTarget"
      class="db-contextual-link-config__mode db-contextual-link-config__field"
    >
      <p>{{ _t('Target page') }}</p>
      <span class="db-contextual-link-config__target">
        <CmkMultitoneIcon name="chain" primary-color="font" size="small" aria-hidden="true" />
        <span class="db-contextual-link-config__target-title">{{ defaultTarget }}</span>
        <span class="db-contextual-link-config__copy">{{ _t('(set by Checkmk)') }}</span>
      </span>
    </div>

    <div
      v-if="selectedChoice === 'inherited'"
      class="db-contextual-link-config__mode db-contextual-link-config__group"
    >
      <div class="db-contextual-link-config__field">
        <p>{{ _t('Target page') }}</p>
        <ContextualLinkTargetPicker
          v-model="handler.inheritedTarget.value"
          :targets="targets"
          :views-error="viewsError"
          :dashboards-error="dashboardsError"
        />
      </div>
      <div class="db-contextual-link-config__field">
        <p>{{ _t('Pass on to target page') }}</p>
        <span class="db-contextual-link-config__always">
          <CmkMultitoneIcon name="checkmark" primary-color="font" size="small" aria-hidden="true" />
          <span>
            {{ _t('Filters from the clicked item') }}
            <span class="db-contextual-link-config__copy">{{ _t('(always passed on)') }}</span>
          </span>
        </span>
        <CmkCheckbox
          v-model="handler.inheritedIncludeContext.value"
          :label="_t('Dashboard & widget filters')"
        />
        <CmkCheckbox v-model="handler.inheritedIncludeTimeRange.value" :label="_t('Time range')" />
      </div>
    </div>

    <div
      v-if="selectedChoice === 'custom'"
      class="db-contextual-link-config__mode db-contextual-link-config__links"
    >
      <div v-for="(link, index) in handler.customLinks.value" :key="link.id">
        <div class="db-contextual-link-config__link-header">
          <CmkCollapsibleTitle
            :title="_t('Link %{n}', { n: index + 1 })"
            v-bind="closedLinks.has(link.id) ? { sideTitle: collapsedSummary(link.target) } : {}"
            :open="!closedLinks.has(link.id)"
            @toggle-open="toggleLink(link.id)"
          />
          <span class="db-contextual-link-config__link-actions">
            <CmkIconButton
              name="clone"
              :title="_t('Duplicate link')"
              @click="handler.duplicateCustomLink(index)"
            />
            <CmkIconButton
              name="delete"
              :title="
                handler.customLinks.value.length === 1
                  ? _t('At least one link is needed')
                  : _t('Delete link')
              "
              :disabled="handler.customLinks.value.length === 1"
              @click="handler.removeCustomLink(index)"
            />
          </span>
        </div>
        <CmkCollapsible :open="!closedLinks.has(link.id)">
          <CmkIndent
            class="db-contextual-link-config__indent db-contextual-link-config__group db-contextual-link-config__link-body"
          >
            <div class="db-contextual-link-config__field">
              <p>{{ _t('Target page') }}</p>
              <ContextualLinkTargetPicker
                v-model="link.target"
                :targets="targets"
                :views-error="viewsError"
                :dashboards-error="dashboardsError"
              />
            </div>
            <div class="db-contextual-link-config__field">
              <p class="db-contextual-link-config__label">
                {{ _t('Link description') }}
                <CmkHelpText
                  :help="
                    _t(
                      'Shown in the link menu when users click an item. Describe how the target page relates to the clicked item, for example: Hosts with the same OS and folder.'
                    )
                  "
                />
              </p>
              <CmkInput
                v-model="link.description"
                field-size="fill"
                :aria-label="_t('Link description')"
              />
            </div>
            <div class="db-contextual-link-config__field">
              <p>{{ _t('Pass on to target page') }}</p>
              <CmkCheckbox
                v-model="link.includeClickedElement"
                :label="_t('Filters from the clicked item')"
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
              <CmkCheckbox
                v-model="link.includeContext"
                :label="_t('Dashboard & widget filters')"
              />
              <CmkCheckbox v-model="link.includeTimeRange" :label="_t('Time range')" />
            </div>
          </CmkIndent>
        </CmkCollapsible>
      </div>
      <CmkInlineButton class="db-contextual-link-config__add-link" @click="handler.addCustomLink()">
        {{ _t('Add another link') }}
      </CmkInlineButton>
    </div>

    <CmkInlineValidation
      v-if="!unavailable && handler.validationErrors.value.length > 0"
      :validation="handler.validationErrors.value"
    />
  </div>
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

.db-contextual-link-config {
  display: flex;
  flex-direction: column;
}

.db-contextual-link-config__choice-description {
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

.db-contextual-link-config__link-actions {
  display: flex;
  gap: var(--dimension-3);
}

.db-contextual-link-config__label {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
}

.db-contextual-link-config__always {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
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
</style>
