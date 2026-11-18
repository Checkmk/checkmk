<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton/CmkButton.vue'
import CmkColorSwatch from 'cmk-ui-library/components/CmkColorSwatch.vue'
import { type SimpleIcons } from 'cmk-ui-library/components/CmkIcon'
import CmkIcon from 'cmk-ui-library/components/CmkIcon/CmkIcon.vue'
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import CmkScrollContainer from 'cmk-ui-library/components/CmkScrollContainer.vue'
import CmkSearchInput from 'cmk-ui-library/components/CmkSearchInput.vue'
import CmkToggleButtonGroup from 'cmk-ui-library/components/CmkToggleButtonGroup.vue'
import { CmkTooltipProvider } from 'cmk-ui-library/components/CmkTooltip'
import ArrowDown from 'cmk-ui-library/components/graphics/ArrowDown.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { useFloatingTarget } from 'cmk-ui-library/lib/useFloatingTarget'
import {
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuPortal,
  DropdownMenuRoot,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger
} from 'reka-ui'
import { computed, ref, useTemplateRef } from 'vue'

import CmkMenuLabel from './CmkMenuLabel.vue'
import type { CmkMenuCategory, CmkMenuItem } from './types'

const SEARCH_FROM_ITEM_COUNT = 9
// The toggle's value for no narrowing; no category may take it.
const ALL_CATEGORIES = ''

const { _t } = usei18n()

const {
  items,
  label,
  searchable = false,
  triggerIcon,
  triggerText,
  triggerVariant = 'button',
  searchPlaceholder,
  categories
} = defineProps<{
  items: CmkMenuItem[]
  /**
   * Names the icon-only trigger and the menu it opens; a button with text is named by it, a
   * field by both.
   */
  label: string
  /** Search is always shown from nine items on. */
  searchable?: boolean
  /** Replaces the trigger's link icon. */
  triggerIcon?: SimpleIcons | undefined
  /** Text next to the trigger's icon; without it, the trigger is icon-only. */
  triggerText?: string | undefined
  /**
   * A field fills its container like a dropdown and shows `triggerText`, or `label` as its
   * placeholder, without an icon.
   */
  triggerVariant?: 'button' | 'field'
  searchPlaceholder?: string | undefined
  /** Offers a toggle below the search that narrows the items to one category, and heads them. */
  categories?: CmkMenuCategory[] | undefined
}>()

const emit = defineEmits<{
  /** The value of a selected value item. */
  select: [value: string]
}>()

const floatingTarget = useFloatingTarget()
const search = useTemplateRef('search')

const open = ref(false)
const query = ref('')
const category = ref(ALL_CATEGORIES)
const keyboardFocusedKey = ref<number | null>(null)

const entries = computed(() =>
  items.map((item, key) => ({
    key,
    item,
    fullLabel: [...item.label]
      .sort((a, b) => (a.line ?? 1) - (b.line ?? 1))
      .map((part) => part.text)
      .join(' – ')
  }))
)

function accessibleName(entry: (typeof entries.value)[number]): string {
  return entry.item.detail ? `${entry.fullLabel} – ${entry.item.detail}` : entry.fullLabel
}

const twoLine = computed(() => items.some((item) => item.label.some((part) => part.line === 2)))

const listMaxHeight = computed(
  () => `calc(9 * var(${twoLine.value ? '--dimension-12' : '--dimension-9'}))`
)

const showSearch = computed(() => searchable || entries.value.length >= SEARCH_FROM_ITEM_COUNT)

const categoryOptions = computed(() =>
  categories === undefined
    ? []
    : [
        { value: ALL_CATEGORIES, title: _t('All'), count: items.length },
        ...categories.map(({ value, title }) => ({
          value,
          title,
          count: items.filter((item) => item.category === value).length
        }))
      ].map(({ value, title, count }) => ({ value, label: `${title} (${count})` }))
)

const visibleEntries = computed(() => {
  const needle = query.value.trim().toLowerCase()
  return entries.value.filter(
    (entry) =>
      entry.fullLabel.toLowerCase().includes(needle) &&
      (category.value === ALL_CATEGORIES || entry.item.category === category.value)
  )
})

/** The visible entries under the heading of their category, in the order of the categories. */
const sections = computed(() => {
  if (categories === undefined) {
    return [{ key: ALL_CATEGORIES, title: undefined, entries: visibleEntries.value }]
  }
  const known = new Set(categories.map(({ value }) => value))
  return [
    ...categories.map(({ value, title }) => ({
      key: value,
      title,
      entries: visibleEntries.value.filter((entry) => entry.item.category === value)
    })),
    {
      key: ALL_CATEGORIES,
      title: undefined,
      entries: visibleEntries.value.filter((entry) => !known.has(entry.item.category ?? ''))
    }
  ].filter((section) => section.entries.length > 0)
})

function onOpenChange(): void {
  query.value = ''
  category.value = ALL_CATEGORIES
}

function focusSearch(event: Event): void {
  if (showSearch.value) {
    event.preventDefault()
    search.value?.focus()
  }
}

function onItemFocus(key: number, event: FocusEvent): void {
  if ((event.target as HTMLElement).matches(':focus-visible')) {
    keyboardFocusedKey.value = key
  }
}
</script>

<template>
  <!-- Remounted with another trigger: the menu would stay anchored to the old one. -->
  <DropdownMenuRoot :key="triggerVariant" v-model:open="open" @update:open="onOpenChange">
    <DropdownMenuTrigger as-child>
      <button
        v-if="triggerVariant === 'field'"
        type="button"
        class="cmk-menu__field"
        :class="{ 'cmk-menu__field--empty': !triggerText }"
        :aria-label="triggerText ? `${label}: ${triggerText}` : label"
      >
        <span class="cmk-menu__field-text">{{ triggerText || label }}</span>
        <ArrowDown
          class="cmk-menu__caret"
          :class="{ 'cmk-menu__caret--open': open }"
          aria-hidden="true"
        />
      </button>
      <CmkButton
        v-else
        class="cmk-menu__trigger"
        size="small"
        :title="triggerText ? undefined : label"
        :aria-label="triggerText ? undefined : label"
      >
        <CmkIcon v-if="triggerIcon" :name="triggerIcon" size="small" aria-hidden="true" />
        <CmkMultitoneIcon
          v-else
          name="chain"
          primary-color="font"
          size="small"
          aria-hidden="true"
        />
        <span v-if="triggerText">{{ triggerText }}</span>
        <ArrowDown
          class="cmk-menu__caret"
          :class="{ 'cmk-menu__caret--open': open }"
          aria-hidden="true"
        />
      </CmkButton>
    </DropdownMenuTrigger>
    <DropdownMenuPortal :to="floatingTarget ?? 'body'">
      <DropdownMenuContent
        class="cmk-menu"
        :class="{ 'cmk-menu--two-line': twoLine, 'cmk-menu--field': triggerVariant === 'field' }"
        side="bottom"
        align="start"
        :side-offset="4"
        prioritize-position
        @open-auto-focus="focusSearch"
      >
        <!-- Tab moves between the search and the category toggle, which the menu would swallow. -->
        <div v-if="showSearch || categories" class="cmk-menu__header" @keydown.tab.stop>
          <!-- Home and End belong to the caret here, not to the menu's item navigation. -->
          <CmkSearchInput
            v-if="showSearch"
            ref="search"
            v-model="query"
            :placeholder="searchPlaceholder ?? _t('Search')"
            inline-search-icon
            :show-submit-button="false"
            @keydown.home.end.stop
          />
          <CmkToggleButtonGroup
            v-if="categories"
            v-model="category"
            :options="categoryOptions"
            size="small"
            spacing="none"
          />
        </div>
        <CmkTooltipProvider>
          <CmkScrollContainer :max-height="listMaxHeight">
            <DropdownMenuGroup
              v-for="section in sections"
              :key="section.key"
              :aria-label="section.title"
            >
              <DropdownMenuLabel v-if="section.title" class="cmk-menu__heading">
                {{ section.title }}
              </DropdownMenuLabel>
              <template v-for="entry in section.entries" :key="entry.key">
                <DropdownMenuItem
                  v-if="'value' in entry.item"
                  class="cmk-menu__item"
                  :aria-label="accessibleName(entry)"
                  @select="emit('select', entry.item.value)"
                  @focus="onItemFocus(entry.key, $event)"
                  @blur="keyboardFocusedKey = null"
                >
                  <CmkColorSwatch
                    v-if="entry.item.color"
                    class="cmk-menu__swatch"
                    :color="entry.item.color"
                  />
                  <CmkMenuLabel
                    :parts="entry.item.label"
                    :full-label="entry.fullLabel"
                    :keyboard-focused="keyboardFocusedKey === entry.key"
                  />
                  <span v-if="entry.item.detail" class="cmk-menu__detail">{{
                    entry.item.detail
                  }}</span>
                  <CmkIcon
                    v-if="entry.item.icon"
                    class="cmk-menu__icon"
                    :name="entry.item.icon"
                    size="small"
                    aria-hidden="true"
                  />
                </DropdownMenuItem>
                <DropdownMenuItem v-else-if="entry.item.links.length === 1" as-child>
                  <a
                    class="cmk-menu__item"
                    :href="entry.item.links[0].url"
                    :aria-label="accessibleName(entry)"
                    @focus="onItemFocus(entry.key, $event)"
                    @blur="keyboardFocusedKey = null"
                  >
                    <CmkColorSwatch
                      v-if="entry.item.color"
                      class="cmk-menu__swatch"
                      :color="entry.item.color"
                    />
                    <CmkMenuLabel
                      :parts="entry.item.label"
                      :full-label="entry.fullLabel"
                      :keyboard-focused="keyboardFocusedKey === entry.key"
                    />
                    <span v-if="entry.item.detail" class="cmk-menu__detail">{{
                      entry.item.detail
                    }}</span>
                    <CmkIcon
                      v-if="entry.item.icon"
                      class="cmk-menu__icon"
                      :name="entry.item.icon"
                      size="small"
                      aria-hidden="true"
                    />
                  </a>
                </DropdownMenuItem>
                <DropdownMenuSub v-else>
                  <DropdownMenuSubTrigger
                    class="cmk-menu__item"
                    :aria-label="accessibleName(entry)"
                    @focus="onItemFocus(entry.key, $event)"
                    @blur="keyboardFocusedKey = null"
                  >
                    <CmkColorSwatch
                      v-if="entry.item.color"
                      class="cmk-menu__swatch"
                      :color="entry.item.color"
                    />
                    <CmkMenuLabel
                      :parts="entry.item.label"
                      :full-label="entry.fullLabel"
                      :keyboard-focused="keyboardFocusedKey === entry.key"
                    />
                    <span v-if="entry.item.detail" class="cmk-menu__detail">{{
                      entry.item.detail
                    }}</span>
                    <CmkIcon
                      v-if="entry.item.icon"
                      class="cmk-menu__icon"
                      :name="entry.item.icon"
                      size="small"
                      aria-hidden="true"
                    />
                    <CmkMultitoneIcon
                      class="cmk-menu__chevron"
                      name="chevron-right"
                      primary-color="font"
                      size="xsmall"
                      aria-hidden="true"
                    />
                  </DropdownMenuSubTrigger>
                  <DropdownMenuPortal :to="floatingTarget ?? 'body'">
                    <DropdownMenuSubContent
                      class="cmk-menu cmk-menu--submenu"
                      :class="{ 'cmk-menu--two-line': twoLine }"
                      :side-offset="1"
                    >
                      <DropdownMenuItem
                        v-for="(link, index) in entry.item.links"
                        :key="index"
                        as-child
                      >
                        <a class="cmk-menu__item cmk-menu__link" :href="link.url">{{
                          link.title
                        }}</a>
                      </DropdownMenuItem>
                    </DropdownMenuSubContent>
                  </DropdownMenuPortal>
                </DropdownMenuSub>
              </template>
            </DropdownMenuGroup>
            <div v-if="visibleEntries.length === 0" class="cmk-menu__empty">
              {{ _t('No results') }}
            </div>
          </CmkScrollContainer>
        </CmkTooltipProvider>
      </DropdownMenuContent>
    </DropdownMenuPortal>
  </DropdownMenuRoot>
</template>

<style scoped>
.cmk-menu__trigger.cmk-menu__trigger {
  gap: var(--dimension-2);
  padding: 0 var(--dimension-3);
  font-weight: var(--font-weight-default);
}

.cmk-menu__caret {
  width: 0.7em;
  color: var(--dropdown-arrow-color);
}

.cmk-menu__caret--open {
  transform: rotate(180deg);
}

.cmk-menu__field {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
  box-sizing: border-box;
  width: 100%;
  height: var(--form-field-height);
  margin: 0;
  padding: 0 var(--dimension-4);
  background-color: var(--default-form-element-bg-color);
  border: none;
  color: var(--font-color);
  font-weight: var(--font-weight-default);
  cursor: pointer;

  &:hover {
    background-color: var(--input-hover-bg-color);
  }

  &:focus-visible {
    outline: revert;
  }
}

.cmk-menu__field--empty {
  color: var(--font-color-dimmed);
}

.cmk-menu__field-text {
  overflow: hidden;
  text-align: left;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* The caret goes to the end of a field, after its text. */
.cmk-menu__field .cmk-menu__caret {
  flex: none;
  margin-left: auto;
}
</style>

<style>
/* The menus are portalled out of this component, so their styles cannot be scoped. */
.cmk-menu {
  z-index: var(--z-index-dropdown-offset);
  box-sizing: border-box;
  width: 360px;
  overflow: hidden;
  background: var(--ux-theme-5);
  border: 1px solid var(--border-color-subtle);
  border-radius: var(--border-radius);
  color: var(--font-color);
}

.cmk-menu--submenu {
  width: max-content;
  min-width: 160px;
  max-width: 260px;
}

/* As wide as its field, and wide enough for a toggle of three categories. */
.cmk-menu--field {
  width: var(--reka-dropdown-menu-trigger-width);
  min-width: 300px;
}

.cmk-menu__header {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-5);
  padding: var(--dimension-5);
  border-bottom: 1px solid var(--border-color-subtle);
}

.cmk-menu__heading {
  padding: var(--dimension-4) var(--dimension-5) var(--dimension-3);
  font-weight: var(--font-weight-bold);
}

.cmk-menu__item {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  height: var(--dimension-9);
  padding: 0 var(--dimension-5);
  color: inherit;
  text-decoration: none;
  white-space: nowrap;
  cursor: pointer;
  user-select: none;

  &[data-highlighted],
  &[data-state='open'] {
    background-color: var(--background-row-hover);
  }
}

/* Fixed-size, so a long label cannot squeeze them. */
.cmk-menu__detail,
.cmk-menu__icon,
.cmk-menu__chevron {
  flex: none;
}

.cmk-menu__detail,
.cmk-menu__icon {
  margin-left: auto;
}

.cmk-menu__detail {
  color: var(--font-color-dimmed);

  + .cmk-menu__icon {
    margin-left: 0;
  }
}

.cmk-menu__link {
  display: block;
  overflow: hidden;
  line-height: var(--dimension-9);
  text-overflow: ellipsis;
}

.cmk-menu--two-line {
  .cmk-menu__item {
    height: var(--dimension-12);

    .cmk-menu__swatch {
      height: var(--dimension-10);
    }
  }

  .cmk-menu__link {
    line-height: var(--dimension-12);
  }
}

.cmk-menu__empty {
  padding: 0 var(--dimension-5);
  line-height: var(--dimension-9);
  color: var(--font-color-dimmed);
}
</style>
