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
import { CmkTooltipProvider } from 'cmk-ui-library/components/CmkTooltip'
import ArrowDown from 'cmk-ui-library/components/graphics/ArrowDown.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { useFloatingTarget } from 'cmk-ui-library/lib/useFloatingTarget'
import {
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuPortal,
  DropdownMenuRoot,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger
} from 'reka-ui'
import { computed, ref, useTemplateRef } from 'vue'

import CmkMenuLabel from './CmkMenuLabel.vue'
import type { CmkMenuItem } from './types'

const SEARCH_FROM_ITEM_COUNT = 9

const { _t } = usei18n()

const {
  items,
  label,
  searchable = false,
  triggerIcon,
  triggerText,
  searchPlaceholder
} = defineProps<{
  items: CmkMenuItem[]
  /** Names the icon-only trigger and the menu it opens; a trigger with text is named by it. */
  label: string
  /** Search is always shown from nine items on. */
  searchable?: boolean
  /** Replaces the trigger's link icon. */
  triggerIcon?: SimpleIcons | undefined
  /** Text next to the trigger's icon; without it, the trigger is icon-only. */
  triggerText?: string | undefined
  searchPlaceholder?: string | undefined
}>()

const emit = defineEmits<{
  /** The value of a selected value item. */
  select: [value: string]
}>()

const floatingTarget = useFloatingTarget()
const search = useTemplateRef('search')

const open = ref(false)
const query = ref('')
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

const twoLine = computed(() => items.some((item) => item.label.some((part) => part.line === 2)))

const listMaxHeight = computed(
  () => `calc(9 * var(${twoLine.value ? '--dimension-12' : '--dimension-9'}))`
)

const showSearch = computed(() => searchable || entries.value.length >= SEARCH_FROM_ITEM_COUNT)

const visibleEntries = computed(() => {
  const needle = query.value.trim().toLowerCase()
  return entries.value.filter((entry) => entry.fullLabel.toLowerCase().includes(needle))
})

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
  <DropdownMenuRoot v-model:open="open" @update:open="query = ''">
    <DropdownMenuTrigger as-child>
      <CmkButton
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
        :class="{ 'cmk-menu--two-line': twoLine }"
        side="bottom"
        align="start"
        :side-offset="4"
        prioritize-position
        @open-auto-focus="focusSearch"
      >
        <!-- Home and End belong to the caret here, not to the menu's item navigation. -->
        <div v-if="showSearch" class="cmk-menu__search" @keydown.home.end.stop>
          <CmkSearchInput
            ref="search"
            v-model="query"
            :placeholder="searchPlaceholder ?? _t('Search')"
            inline-search-icon
            :show-submit-button="false"
          />
        </div>
        <CmkTooltipProvider>
          <CmkScrollContainer :max-height="listMaxHeight">
            <template v-for="entry in visibleEntries" :key="entry.key">
              <DropdownMenuItem
                v-if="'value' in entry.item"
                class="cmk-menu__item"
                :aria-label="entry.fullLabel"
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
                  :aria-label="entry.fullLabel"
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
                  :aria-label="entry.fullLabel"
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
                      <a class="cmk-menu__item cmk-menu__link" :href="link.url">{{ link.title }}</a>
                    </DropdownMenuItem>
                  </DropdownMenuSubContent>
                </DropdownMenuPortal>
              </DropdownMenuSub>
            </template>
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
  border-radius: var(--dimension-2);
  color: var(--font-color);
}

.cmk-menu--submenu {
  width: max-content;
  min-width: 160px;
  max-width: 260px;
}

.cmk-menu__search {
  padding: var(--dimension-5);
  border-bottom: 1px solid var(--border-color-subtle);
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
.cmk-menu__icon,
.cmk-menu__chevron {
  flex: none;
}

.cmk-menu__icon {
  margin-left: auto;
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
