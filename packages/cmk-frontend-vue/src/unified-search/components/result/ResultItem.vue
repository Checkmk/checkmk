<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { DynamicIcon } from 'cmk-shared-typing/typescript/icon'
import type {
  UnifiedSearchResultItemInlineButton,
  UnifiedSearchResultTarget
} from 'cmk-shared-typing/typescript/unified_search'
import { computed, onBeforeUnmount, ref, useTemplateRef } from 'vue'

import { immediateWatch } from '@/lib/watch'

import CmkButton from '@/components/CmkButton.vue'
import CmkDynamicIcon from '@/components/CmkIcon/CmkDynamicIcon/CmkDynamicIcon.vue'
import CmkZebra from '@/components/CmkZebra.vue'

import { showLoadingTransition } from '@/loading-transition/loadingTransition'
import { getSearchUtils } from '@/unified-search/providers/search-utils'

import ResultItemTitle from './ResultItemTitle.vue'

export interface ResultItemProps {
  idx: number
  icon?: DynamicIcon | undefined
  title: string
  html?: string | undefined
  target?: UnifiedSearchResultTarget | undefined
  inline_buttons?: UnifiedSearchResultItemInlineButton[] | undefined
  context?: string | undefined
  focus?: boolean | undefined
  breadcrumb?: string[] | undefined
  zebra?: boolean | undefined
  indented?: boolean | undefined
}
const props = defineProps<ResultItemProps>()

const focusRef = useTemplateRef('item-focus')
const focusInlineRef = useTemplateRef('item-focus-inline')
const currentlySelected = ref<number>(-1)
const searchUtils = getSearchUtils()

const wrapperComponent = computed(() => (props.zebra ? CmkZebra : 'div'))
const wrapperProps = computed(() => (props.zebra ? { num: props.idx } : {}))

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

function navigateToTarget(title: string, target?: UnifiedSearchResultTarget | undefined) {
  if (target) {
    window.open(target.url, 'main')
    if (target.transition) {
      showLoadingTransition(target.transition, title)
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
    <component :is="wrapperComponent" v-bind="wrapperProps" class="result-item-handler-wrapper">
      <a
        v-if="props.target"
        ref="item-focus"
        :href="props.target.url"
        target="main"
        class="result-item-handler"
        :class="{ focus: props.focus, indented: props.indented }"
        @click="target?.transition && showLoadingTransition(target.transition, props.title)"
      >
        <div v-if="props.icon" class="result-item-inner-start">
          <div class="result-item-icon">
            <CmkDynamicIcon :spec="props.icon" />
          </div>
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
      <button
        v-else
        ref="item-focus"
        class="result-item-handler"
        :class="{ focus: props.focus, indented: props.indented }"
      >
        <div v-if="props.icon" class="result-item-inner-start">
          <div class="result-item-icon">
            <CmkDynamicIcon :spec="props.icon" />
          </div>
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
      <div
        v-for="(ib, i) in props.inline_buttons"
        :key="i"
        class="result-item-handler inline"
        :class="{ indented: props.indented }"
      >
        <CmkButton
          ref="item-focus-inline"
          class="inline-button"
          @click="navigateToTarget(ib.title, ib.target)"
        >
          <div v-if="ib.icon" class="result-item-inner-start">
            <CmkDynamicIcon :spec="ib.icon" size="small" class="result-item-icon" />
          </div>
          <div class="result-item-inner-end">
            {{ ib.title }}
          </div>
        </CmkButton>
      </div>
    </component>
  </li>
</template>

<style scoped>
/* stylelint-disable checkmk/vue-bem-naming-convention */

.result-item {
  list-style-type: none;

  .result-item-icon {
    margin-right: var(--spacing);
  }

  .result-item-handler-wrapper {
    position: relative;
    width: 100%;
    overflow: hidden;
    height: auto;
    display: flex;
    flex-direction: row;
    align-items: stretch;
    justify-content: space-between;
  }

  .result-item-handler {
    padding: var(--dimension-3) var(--dimension-4);
    margin: 0;
    background: var(--default-bg-color);
    text-decoration: none;
    justify-content: space-between;
    outline-color: var(--success);
    border-radius: 0;
    display: flex;
    flex-direction: row;
    border: 1px solid var(--default-bg-color);
    flex: 10;
    width: 100%;
    box-sizing: border-box;

    &.indented {
      padding: var(--dimension-3) var(--dimension-8);
    }

    &:hover {
      background-color: var(--ux-theme-5);
      border: 1px solid var(--ux-theme-5);
    }

    &.inline {
      padding: 0 var(--spacing);
      flex: 1;
      margin-left: 1px;
      box-sizing: border-box;
      height: auto;
      position: relative;
      align-items: center;

      &:hover {
        background-color: var(--default-bg-color);
        border: 1px solid var(--default-bg-color);
      }

      .inline-button {
        height: 20px;
        width: 100%;

        &:active,
        &:focus {
          border: 1px solid var(--success);
          outline: none;
        }

        .result-item-icon {
          margin-right: var(--dimension-4);
        }
      }
    }

    &:active,
    &:focus {
      border: 1px solid var(--success);
      outline: none;
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
    font-weight: var(--font-weight-default);
    min-width: 0;
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
</style>
