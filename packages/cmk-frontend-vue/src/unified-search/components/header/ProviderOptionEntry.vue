<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { immediateWatch } from '@/lib/watch'
import { useTemplateRef } from 'vue'
import usei18n from '@/lib/i18n'
import type { ProviderOption } from '@/unified-search/providers/search-utils.types'

export interface ProviderOptionEntryProps {
  idx: number
  option: ProviderOption
  focus?: boolean | undefined
  active?: boolean | undefined
}

const { t } = usei18n('unified-search-app')
const props = defineProps<ProviderOptionEntryProps>()

const focusRef = useTemplateRef('filter-focus')
immediateWatch(
  () => ({ newFocus: props.focus }),
  async ({ newFocus }) => {
    if (newFocus) {
      focusRef.value?.focus()
    }
  }
)
</script>

<template>
  <li role="option">
    <button ref="filter-focus" :class="{ active }">
      <span>{{ t(['filter', option.type, option.value].join('-'), option.title) }}</span>
    </button>
  </li>
</template>

<style scoped>
li {
  line-height: 20px;

  > button {
    background: transparent;
    border: 1px solid transparent;
    width: 100%;
    padding: var(--dimension-padding-2) var(--dimension-padding-4);
    margin: 0;
    text-align: left;
    font-weight: normal;
    outline: none;
    border-radius: 0;

    &:focus {
      border: 1px solid var(--success);
    }

    &:hover,
    &.active {
      color: var(--success);
    }

    > span {
      font-weight: normal;
    }
  }
}
</style>
