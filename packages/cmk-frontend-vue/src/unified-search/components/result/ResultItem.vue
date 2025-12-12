<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type {
  UnifiedSearchResultItemInlineButton,
  UnifiedSearchResultTarget
} from 'cmk-shared-typing/typescript/unified_search'
import { onBeforeUnmount, ref, useTemplateRef } from 'vue'

import { immediateWatch } from '@/lib/watch'

import type { CmkIconProps } from '@/components/CmkIcon'
import CmkIcon from '@/components/CmkIcon'
import CmkZebra from '@/components/CmkZebra.vue'

import { showLoadingTransition } from '@/loading-transition/loadingTransition'
import { getSearchUtils } from '@/unified-search/providers/search-utils'

import ResultItemTitle from './ResultItemTitle.vue'

export interface ResultItemProps {
  idx: number
  icon?: CmkIconProps | undefined
  title: string
  html?: string | undefined
  target?: UnifiedSearchResultTarget | undefined
  inline_buttons?: UnifiedSearchResultItemInlineButton[] | undefined
  context?: string | undefined
  focus?: boolean | undefined
  breadcrumb?: string[] | undefined
}
const props = defineProps<ResultItemProps>()

const focusRef = useTemplateRef('item-focus')
const focusInlineRef = useTemplateRef('item-focus-inline')
const currentlySelected = ref<number>(-1)
const searchUtils = getSearchUtils()

const shortcutCallbackIds = ref<string[]>([])
shortcutCallbackIds.value.push(searchUtils.shortCuts.onArrowLeft(toggleLeft))
shortcutCallbackIds.value.push(searchUtils.shortCuts.onArrowRight(toggleRight))

function toggleLeft() {
  toggleInline(-1)
}

function toggleRight() {
  toggleInline(+1)
}

function toggleInline(d: number, set: boolean = false) {
  if (props.focus) {
    if (set) {
      currentlySelected.value = d
    } else {
      currentlySelected.value += d
    }

    if (props.inline_buttons && props.inline_buttons.length > 0) {
      if (currentlySelected.value < 0) {
        currentlySelected.value = props.inline_buttons.length
      }

      if (currentlySelected.value > props.inline_buttons.length) {
        currentlySelected.value = 0
      }
    }

    setFocus()
  }
}

function setFocus() {
  if (currentlySelected.value >= 0) {
    if (currentlySelected.value === 0) {
      focusRef.value?.focus()
    } else {
      const fE = focusInlineRef.value ? focusInlineRef.value[currentlySelected.value - 1] : null
      if (fE) {
        fE.focus()
      }
    }
  }
}

immediateWatch(
  () => ({ newFocus: props.focus }),
  async ({ newFocus }) => {
    if (newFocus) {
      toggleInline(0, true)
    } else {
      toggleInline(-1, true)
    }
  }
)

onBeforeUnmount(() => {
  searchUtils.shortCuts.remove(shortcutCallbackIds.value)
})
</script>

<template>
  <li class="result-item">
    <CmkZebra :num="idx" class="result-item-handler-wrapper">
      <a
        v-if="props.target"
        ref="item-focus"
        :href="props.target.url"
        target="main"
        class="result-item-handler"
        :class="{ focus: props.focus }"
        @click="target?.transition && showLoadingTransition(target.transition, props.title)"
      >
        <div v-if="props.icon" class="result-item-inner-start">
          <CmkIcon
            :name="props.icon.name"
            :rotate="props.icon.rotate"
            :size="props.icon.size"
            class="result-item-icon"
          ></CmkIcon>
        </div>
        <div class="result-item-inner-end">
          <span
            v-if="props.breadcrumb && props.breadcrumb.length > 0"
            class="result-item-breadcrumb"
            >{{ props.breadcrumb.join(' > ') }}</span
          >
          <ResultItemTitle
            :title="props.html ? props.html : props.title"
            :context="props.context ? props.context : ''"
          ></ResultItemTitle>
        </div>
      </a>
      <button v-else ref="item-focus" class="result-item-handler" :class="{ focus: props.focus }">
        <div v-if="props.icon" class="result-item-inner-start">
          <CmkIcon
            :name="props.icon.name"
            :rotate="props.icon.rotate"
            :size="props.icon.size"
            class="result-item-icon"
          ></CmkIcon>
        </div>
        <div class="result-item-inner-end">
          <span
            v-if="props.breadcrumb && props.breadcrumb.length > 0"
            class="result-item-breadcrumb"
            >{{ props.breadcrumb.join(' > ') }}</span
          >
          <ResultItemTitle
            :title="props.html ? props.html : props.title"
            :context="props.context ? props.context : ''"
          ></ResultItemTitle>
        </div>
      </button>
      <a
        v-for="(ib, i) in props.inline_buttons"
        ref="item-focus-inline"
        :key="i"
        :href="ib.target.url"
        target="main"
        class="result-item-handler inline"
        @click="ib.target?.transition && showLoadingTransition(ib.target.transition, ib.title)"
      >
        <div v-if="ib.icon" class="result-item-inner-start">
          <CmkIcon
            :name="ib.icon.name"
            :size="ib.icon.size || undefined"
            class="result-item-icon"
          ></CmkIcon>
        </div>
        <div class="result-item-inner-end">
          <ResultItemTitle :title="ib.title" context=""></ResultItemTitle>
        </div>
      </a>
    </CmkZebra>
  </li>
</template>

<style scoped>
/* stylelint-disable checkmk/vue-bem-naming-convention */
.result-item {
  list-style-type: none;

  .result-item-handler-wrapper {
    width: 100%;
    height: auto;
    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
  }

  .result-item-handler {
    padding: var(--spacing);
    margin: 0;
    background: var(--default-bg-color);
    text-decoration: none;
    justify-content: space-between;
    outline-color: var(--success);
    border-radius: 0;
    display: flex;
    flex-direction: row;
    box-sizing: content-box;
    border: 1px solid var(--default-bg-color);
    flex: 10;

    &:hover {
      background-color: var(--ux-theme-5);
      border: 1px solid var(--ux-theme-5);
    }

    &:active,
    &:focus {
      border: 1px solid var(--success);
      outline: none;
    }

    &.inline {
      flex: 1;
      margin-left: 1px;
      min-height: 54px;
      box-sizing: border-box;
    }
  }

  .result-item-inner-start {
    display: flex;
    flex-direction: column;
    justify-content: center;
  }

  .result-item-inner-end {
    display: flex;
    flex-direction: column;
    flex: 5;
    justify-content: center;
    align-items: flex-start;
  }
}

.result-item-breadcrumb {
  text-transform: capitalize;
  margin-bottom: var(--spacing-half);
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
}

.result-item-title {
  &::first-letter {
    text-transform: capitalize;
  }

  font-weight: bold;
}

.result-item-icon {
  margin-right: var(--spacing);
}
</style>
