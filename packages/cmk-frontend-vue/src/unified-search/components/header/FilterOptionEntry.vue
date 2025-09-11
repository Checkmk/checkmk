<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { useTemplateRef } from 'vue'

import { untranslated } from '@/lib/i18n'
import { immediateWatch } from '@/lib/watch'

import CmkChip from '@/components/CmkChip.vue'

import type { FilterOption } from '@/unified-search/providers/search-utils.types'

export interface FilterOptemProps {
  idx: number
  option: FilterOption
  focus?: boolean | undefined
  active?: boolean | undefined
}

const props = defineProps<FilterOptemProps>()

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
      <span>
        <CmkChip
          :color="option.type === 'provider' ? 'success' : 'default'"
          :content="untranslated(option.value)"
          size="small"
        ></CmkChip
      ></span>
      <span>{{ option.title }}</span>
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
    padding: var(--spacing);
    margin: 0;
    text-align: left;
    font-weight: normal;
    outline: none;
    border-radius: 0;

    &:focus {
      border: 1px solid var(--success);
    }

    /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
    &:hover,
    &.active {
      color: var(--success);
    }

    > span {
      font-weight: normal;
    }

    > span:first-of-type {
      display: inline-block;
      width: 45px;
    }
  }

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  &.provider {
    > button > span:first-of-type {
      width: 85px;
    }
  }
}
</style>
