<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { DynamicIcon } from 'cmk-shared-typing/typescript/icon'
import {
  type UnifiedSearchApiResponse,
  type UnifiedSearchResultItem
} from 'cmk-shared-typing/typescript/unified_search'
import { type Ref, onBeforeUnmount, ref } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'
import { immediateWatch } from '@/lib/watch'

import CmkDynamicIcon from '@/components/CmkIcon/CmkDynamicIcon/CmkDynamicIcon.vue'
import CmkScrollContainer from '@/components/CmkScrollContainer.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'

import ResultItem from '@/unified-search/components/result/ResultItem.vue'
import ResultList from '@/unified-search/components/result/ResultList.vue'
import { HistoryEntry } from '@/unified-search/lib/searchHistory'
import type { UnifiedSearchError } from '@/unified-search/lib/unified-search'
import { getSearchUtils } from '@/unified-search/providers/search-utils'

import UnifiedSearchEmptyResults from './UnifiedSearchEmptyResults.vue'

export interface UnifiedSearchResultGroup {
  id: string
  title: string
  items: UnifiedSearchResultItem[]
  ref: Ref<boolean>
  showAll: Ref<boolean>
  icon?: DynamicIcon | undefined
}

const MAX_ITEMS_SHOW_ALL = 5

const { _t } = usei18n()

const searchUtils = getSearchUtils()
const currentlySelected = ref<number>(-1)
const currentlySelectedGroup = ref<number>(-1)
const inited = ref<boolean>(false)
const results = ref<UnifiedSearchResultItem[]>([])
const groupedResults = ref<UnifiedSearchResultGroup[]>([])
searchUtils.input?.onSetFocus(() => {
  currentlySelected.value = -1
})
searchUtils.onResetSearch(() => {
  currentlySelected.value = -1
})

const shortcutCallbackIds = ref<string[]>([])
shortcutCallbackIds.value.push(searchUtils.shortCuts.onArrowDown(toggleDown))
shortcutCallbackIds.value.push(searchUtils.shortCuts.onArrowUp(toggleUp))
shortcutCallbackIds.value.push(searchUtils.shortCuts.onCtrlArrowDown(jumpDown))
shortcutCallbackIds.value.push(searchUtils.shortCuts.onCtrlArrowUp(jumpUp))

function jumpUp() {
  calcCurrentlySelectedGroup(-1)
}

function jumpDown() {
  calcCurrentlySelectedGroup(+1)
}

function toggleDown() {
  calcCurrentlySelected(+1)
}

function toggleUp() {
  calcCurrentlySelected(-1)
}

function calcCurrentlySelectedGroup(d: number, set: boolean = false) {
  // Guard clause - exit early if conditions aren't met
  if (
    !searchUtils.result.grouping.value ||
    searchUtils.input.suggestionsActive.value ||
    searchUtils.input.providerSelectActive.value ||
    searchUtils.input.searchOperatorSelectActive.value ||
    !searchResultNotEmpty()
  ) {
    return
  }

  // Update the selected group value
  currentlySelectedGroup.value = set ? d : currentlySelectedGroup.value + d

  const curGroupLength = groupedResults.value.length || 0

  // Handle out of bounds - too high or at boundary
  if (currentlySelectedGroup.value === -1 || currentlySelectedGroup.value > curGroupLength - 1) {
    currentlySelectedGroup.value = -1
    searchUtils.input?.setFocus()
    return
  }

  // Handle out of bounds - too low
  if (currentlySelectedGroup.value < -1) {
    currentlySelectedGroup.value = curGroupLength - 1
  }

  if (d < 0) {
    const nextGroupLength = getGroupItemLength(currentlySelectedGroup.value)
    currentlySelected.value = nextGroupLength - 1
  } else {
    currentlySelected.value = 0
  }
}

function getGroupItemLength(gdx: number): number {
  if (searchUtils.result.grouping.value) {
    const curGroup = groupedResults.value[gdx]
    return curGroup?.ref
      ? curGroup?.showAll || curGroup.items.length <= MAX_ITEMS_SHOW_ALL
        ? curGroup.items.length
        : MAX_ITEMS_SHOW_ALL
      : 0
  } else {
    return results.value.length || 0
  }
}

function calcCurrentlySelected(d: number, set: boolean = false) {
  // Guard clause - exit early if conditions aren't met
  if (
    searchUtils.input.suggestionsActive.value ||
    searchUtils.input.providerSelectActive.value ||
    searchUtils.input.searchOperatorSelectActive.value ||
    !searchResultNotEmpty()
  ) {
    return
  }

  // Update the selected value
  currentlySelected.value = set ? d : currentlySelected.value + d

  const curGroupLength = getGroupItemLength(currentlySelectedGroup.value)

  // Handle out of bounds - too high or at boundary
  if (currentlySelected.value === -1 || currentlySelected.value > curGroupLength - 1) {
    currentlySelected.value = -1

    if (searchUtils.result.grouping.value) {
      calcCurrentlySelectedGroup(d)
      const nextGroupLength = getGroupItemLength(currentlySelectedGroup.value)
      currentlySelected.value = d < 0 ? nextGroupLength - 1 : 0
    } else {
      searchUtils.input?.setFocus()
    }
    return
  }

  // Handle out of bounds - too low
  if (currentlySelected.value < -1) {
    if (searchUtils.result.grouping.value) {
      currentlySelectedGroup.value -= 1

      if (currentlySelectedGroup.value === -1) {
        currentlySelected.value = -1
        searchUtils.input?.setFocus()
        return
      }

      if (currentlySelectedGroup.value < -1) {
        currentlySelectedGroup.value = groupedResults.value.length - 1
      }

      const nextGroupLength = getGroupItemLength(currentlySelectedGroup.value)
      currentlySelected.value = nextGroupLength - 1
    } else {
      currentlySelected.value = curGroupLength - 1
    }
  }
}

function handleItemClick(item: UnifiedSearchResultItem) {
  searchUtils.history?.add(new HistoryEntry(searchUtils.query.toQueryLike(), item))
  searchUtils.resetSearch()
  searchUtils.closeSearch()
}

searchUtils.result.onSetResultGrouping(updateView)
function updateView(_grouping: boolean) {
  prepareResults(results.value)
}

const isFocused = (i: number | null, g: number | null = null): boolean => {
  if (i === null) {
    return currentlySelectedGroup.value === g && currentlySelected.value === -1
  } else {
    return currentlySelected.value === i && (g === null || currentlySelectedGroup.value === g)
  }
}

const props = defineProps<{
  result?: UnifiedSearchApiResponse | undefined
  error?: UnifiedSearchError | undefined
}>()

function onCheckGrouping(grouping: boolean) {
  searchUtils.result.setResultGrouping(grouping)
}

function prepareResults(newResults: UnifiedSearchResultItem[]) {
  inited.value = false
  if (searchUtils.result.grouping) {
    const grouped = newResults.reduce(
      (acc, item) => {
        const key = `${item.provider}:${item.topic}`
        if (!acc[key]) {
          acc[key] = []
        }
        acc[key].push(item)
        return acc
      },
      {} as Record<string, UnifiedSearchResultItem[]>
    )

    groupedResults.value = Object.entries(grouped).map(([key, items]) => ({
      id: key,
      title: key.split(':')[1] || key, // Use topic as title
      items,
      icon: items[0] ? items[0]?.icon : undefined,
      ref: searchUtils.result.getGroupPersistentRef(searchUtils.id, key),
      showAll: ref<boolean>(false)
    }))
  } else {
    groupedResults.value = []
  }
  results.value = newResults
  inited.value = true
}

immediateWatch(
  () => ({ newResult: props.result }),
  async ({ newResult }) => {
    if (newResult) {
      prepareResults(newResult.results)
    }
  }
)

onBeforeUnmount(() => {
  searchUtils.shortCuts.remove(shortcutCallbackIds.value)
})

function searchResultNotEmpty(): boolean {
  return (
    (!searchUtils.result.grouping.value && results.value && results.value.length > 0) ||
    (searchUtils.result.grouping.value && groupedResults.value && groupedResults.value.length > 0)
  )
}
</script>

<template>
  <div v-if="searchResultNotEmpty()" class="cmk-unified-search-result-tabs">
    <div>
      <CmkHeading type="h4" class="result-heading">
        {{ _t('Results') }} ({{ results.length }})
        <CmkCheckbox
          v-model="searchUtils.result.grouping.value"
          :label="_t('Group results by topic')"
          class="result-heading__grouping"
          @update:model-value="onCheckGrouping"
        ></CmkCheckbox>
      </CmkHeading>
    </div>
    <CmkScrollContainer max-height="calc(100vh - 210px)">
      <template v-if="searchUtils.result.grouping.value">
        <template v-for="(group, gdx) of groupedResults" :key="group.id">
          <CmkHeading type="h4" class="result-group-heading">
            <div class="result-group-heading__icon">
              <CmkDynamicIcon v-if="group.icon" :spec="group.icon" />
            </div>
            <span>{{ group.title.concat(` (${group.items.length})`) as TranslatedString }}</span>
          </CmkHeading>
          <div>
            <ResultList
              v-model="group.showAll"
              :use-show-all="group.items.length > MAX_ITEMS_SHOW_ALL"
              :max-show-all="MAX_ITEMS_SHOW_ALL"
            >
              <ResultItem
                v-for="(item, idx) in group.items"
                ref="recently-viewed-item"
                :key="item.target ? item.target.url : item.title"
                :idx="idx"
                :title="item.title"
                :context="item.context"
                :inline_buttons="item.inline_buttons"
                :target="item.target"
                :html="searchUtils.highlightQuery(item.title)"
                :focus="isFocused(idx, gdx)"
                @keydown.enter="
                  () => {
                    handleItemClick(item)
                  }
                "
                @click="
                  () => {
                    handleItemClick(item)
                  }
                "
              ></ResultItem>
            </ResultList>
          </div>
        </template>
      </template>

      <ResultList v-else>
        <ResultItem
          v-for="(item, idx) in results"
          ref="recently-viewed-item"
          :key="item.target ? item.target.url : item.title"
          :idx="idx"
          :title="item.title"
          :context="item.context"
          :icon="item.icon"
          :inline_buttons="item.inline_buttons"
          :target="item.target"
          :html="searchUtils.highlightQuery(item.title)"
          :breadcrumb="searchUtils.breadcrumb(item.provider, item.topic)"
          :focus="isFocused(idx)"
          @keydown.enter="
            () => {
              handleItemClick(item)
            }
          "
          @click="
            () => {
              handleItemClick(item)
            }
          "
        ></ResultItem>
      </ResultList>
    </CmkScrollContainer>
  </div>
  <UnifiedSearchEmptyResults
    v-if="(inited && !searchResultNotEmpty()) || error"
    :error="error"
  ></UnifiedSearchEmptyResults>
</template>

<style scoped>
/* stylelint-disable checkmk/vue-bem-naming-convention */

.result-heading {
  margin-bottom: var(--spacing);
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;

  .result-heading__grouping {
    font-weight: var(--font-weight-default);
  }

  .result-heading__info {
    font-weight: var(--font-weight-default);
  }
}

.arrow-key {
  width: 11px;
  display: inline-flex;
  height: 12px;
  margin-bottom: -4px;

  &::after {
    font-size: 21px;
    position: absolute;
    margin: -4px 0 0 -5px;
  }

  &.left::after {
    content: '\2190';
  }

  &.right::after {
    content: '\2192';
  }

  &.up::after {
    content: '\2191';
    font-size: 12px;
    margin: 0;
  }

  &.down::after {
    content: '\2193';
    font-size: 12px;
    margin: 0;
  }

  &.enter::after {
    content: '\21B5';
  }
}

.cmk-unified-search-tab-info {
  position: absolute;
  right: var(--spacing-double);
  margin-top: 3px;
  line-height: 14px;
  font-size: var(--font-size-small);
  font-weight: var(--font-weight-default);
  opacity: 0.5;

  .arrow-key {
    width: 11px;
    display: inline-flex;
    height: 12px;
    margin-bottom: -4px;

    &::after {
      font-size: 21px;
      position: absolute;
      margin: -4px 0 0 -5px;
    }

    &.left::after {
      content: '\2190';
    }

    &.right::after {
      content: '\2192';
    }
  }
}

.cmk-unified-search-result-tabs {
  margin: var(--spacing-double);
  height: 100%;
}

.result-group-heading {
  text-transform: capitalize;
  margin: var(--dimension-6) 0 var(--dimension-3);
  border: 1px solid transparent;
  display: flex;

  .result-group-heading__icon {
    margin-right: var(--dimension-4);
  }
}
</style>
