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

import CmkButton from '@/components/CmkButton.vue'
import type { CmkIconProps, IconSizeNames } from '@/components/CmkIcon'
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

const navigateToTarget = (title: string, target?: UnifiedSearchResultTarget | undefined) => {
  if (target) {
    window.open(target.url, 'main')
    if (target.transition) {
      showLoadingTransition(target.transition, title)
    }
  }
}
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
        <div
          v-for="(ib, i) in props.inline_buttons"
          ref="item-focus-inline"
          :key="i"
          class="inline"
        >
          <CmkButton
            variant="secondary"
            role="link"
            @click="navigateToTarget(props.title, ib.target)"
          >
            <CmkIcon
              v-if="ib.icon"
              variant="inline"
              :name="ib.icon.name"
              :size="(ib.icon.size as IconSizeNames) || undefined"
            />
            {{ ib.title }}
          </CmkButton>
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
    </CmkZebra>
  </li>
</template>

<style scoped>
/* stylelint-disable checkmk/vue-bem-naming-convention */
.result-item {
  list-style-type: none;

  .result-item-handler-wrapper {
    width: 100%;
    overflow: hidden;
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
    font-weight: var(--font-weight-default);
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
