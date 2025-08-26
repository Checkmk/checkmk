<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { useTemplateRef } from 'vue'

import { immediateWatch } from '@/lib/watch'

import type { FilterOption } from '@/unified-search/providers/search-utils.types'

export interface SearchOperatorProps {
  idx: number
  option: FilterOption
  focus?: boolean | undefined
}

const props = defineProps<SearchOperatorProps>()

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
    <button ref="filter-focus">
      <span>{{ option.title }}</span>
      <span>{{ option.value }}</span>
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
    padding: var(--dimension-2) var(--dimension-4);
    margin: 0;
    text-align: left;
    font-weight: normal;
    outline: none;
    border-radius: 0;
    display: flex;
    justify-content: space-between;

    &:focus {
      border: 1px solid var(--success);
    }

    &:hover {
      color: var(--success);
    }

    > span {
      font-weight: normal;
    }
  }
}
</style>
