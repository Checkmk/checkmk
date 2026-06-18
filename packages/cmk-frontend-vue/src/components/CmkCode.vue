<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkButton from '@/components/CmkButton'
import CmkCopy from '@/components/CmkCopy.vue'
import CmkIcon from '@/components/CmkIcon'
import CmkIconButton from '@/components/CmkIconButton.vue'
import CmkScrollContainer from '@/components/CmkScrollContainer.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'

const { _t } = usei18n()

const props = defineProps<{
  title?: TranslatedString
  codeText: string
  width?: 'default' | 'fill'
  copyButtonTestId?: string
}>()

const MAX_LINES = 10

const isExpanded = ref(false)

const codeLines = computed(() => props.codeText.split('\n'))
const displayedCode = computed(() => {
  if (isExpanded.value || codeLines.value.length <= MAX_LINES) {
    return props.codeText
  }
  return codeLines.value.slice(0, MAX_LINES).join('\n')
})
const shouldShowToggle = computed(() => codeLines.value.length > MAX_LINES)

const toggleExpansion = () => {
  isExpanded.value = !isExpanded.value
}
const containerClasses = computed(() => ({
  'has-toggle': shouldShowToggle.value,
  expanded: isExpanded.value,
  'cmk-code__is-wide': props.width === 'fill'
}))
</script>

<template>
  <div>
    <CmkHeading v-if="title" type="h4" class="cmk-code__heading">{{ title }}</CmkHeading>
    <div class="code_wrapper">
      <div class="code_container" :class="containerClasses">
        <CmkScrollContainer type="outer" class="code_scroll_container">
          <pre><code v-text="displayedCode"></code></pre>
        </CmkScrollContainer>
        <div v-if="shouldShowToggle && !isExpanded" class="fade_overlay"></div>
        <div v-if="shouldShowToggle" class="toggle_button_container">
          <CmkButton variant="secondary" class="toggle_button" @click="toggleExpansion">
            <CmkIcon
              name="tree-closed"
              variant="inline"
              size="small"
              class="toggle_icon"
              :class="{ expanded: isExpanded }"
            />
            {{ isExpanded ? _t('Show less') : _t('Show more') }}
          </CmkButton>
        </div>
      </div>
      <CmkCopy :text="codeText">
        <CmkIconButton
          name="cmkcode-copied"
          size="xxlarge"
          class="copy_button"
          :data-testId="copyButtonTestId"
        />
      </CmkCopy>
    </div>
  </div>
</template>

<style scoped>
.cmk-code__heading {
  margin-bottom: var(--dimension-3);
  color: var(--font-color);
  font-weight: 400;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.code_wrapper {
  display: flex;
  align-items: flex-start;
  margin: var(--spacing) 0 var(--spacing) 0;
  gap: var(--dimension-4);
  max-width: 100%;

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  .code_container {
    position: relative;
    font-family: monospace;
    font-size: var(--font-size-normal, 12px);
    font-style: normal;
    font-weight: 400;
    line-height: normal;
    padding: var(--dimension-4) var(--dimension-5) var(--dimension-3) var(--dimension-5);
    color: var(--font-color);
    border-radius: var(--border-radius);
    border: var(--border-width-1, 1px) solid var(--code-background-color);
    background: var(--code-background-color);
    max-width: 100%;
    min-width: 0;

    --scroll-bar-thickness: 20px;

    &.cmk-code__is-wide {
      width: 100%;
    }

    /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
    .code_scroll_container {
      overflow-x: auto;
      padding-bottom: var(--dimension-3); /* Firefox will place the scrollbar on top of it */
    }

    /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
    &.has-toggle:not(.expanded) .code_scroll_container {
      /* Add more space to avoid the scrollbar being hidden behind the fade overlay */
      padding-bottom: var(--scroll-bar-thickness);
    }

    pre {
      margin: 0;
      white-space: pre;
    }

    /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
    .fade_overlay {
      position: absolute;
      z-index: var(--z-index-dropdown-offset);
      bottom: var(--scroll-bar-thickness);
      left: 0;
      right: 0;
      height: 60px;
      background: linear-gradient(transparent, var(--code-background-color));
      pointer-events: none;
    }

    /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
    .toggle_button_container {
      position: absolute;
      left: 50%;
      transform: translateX(-50%);
      z-index: var(--z-index-base) + 1;
    }

    /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
    &:not(.expanded) .toggle_button_container {
      bottom: 28px;
    }

    /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
    &.expanded .toggle_button_container {
      position: relative;
      left: auto;
      transform: none;
      margin-top: var(--dimension-4);
      text-align: center;
      width: 100%;
    }

    /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
    .toggle_button {
      font-size: var(--font-size-normal);
      padding: 0 var(--dimension-4);
      border-color: var(--font-color);
      color: var(--font-color);
      display: inline-flex;
      align-items: center;
      gap: var(--dimension-3);
    }

    /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
    .toggle_icon {
      flex-shrink: 0;
      transition: transform 0.2s ease;

      /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
      &.expanded {
        transform: rotate(-90deg);
      }

      /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
      &:not(.expanded) {
        transform: rotate(90deg);
      }
    }
  }

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  .copy_button {
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
  }
}
</style>
