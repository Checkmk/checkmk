<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, nextTick, onMounted, useTemplateRef } from 'vue'

import usei18n from '@/lib/i18n'

const { _t } = usei18n()
const props = defineProps<{
  useShowAll?: boolean | undefined
  maxShowAll?: number | undefined
}>()

const showAll = defineModel<boolean>({ default: false })

const resultList = useTemplateRef('result-list')

const showAllBtnText = computed(() => {
  if (showAll.value) {
    return _t('Show less')
  }

  return _t('Show all')
})

function applyShowAll() {
  if (resultList.value) {
    const items: HTMLLinkElement[] = [].slice
      .call(resultList.value.children)
      .slice(props.maxShowAll)
    for (const item of items) {
      if (showAll.value) {
        item.classList.remove('unified-search-result-list--hide')
      } else {
        item.classList.add('unified-search-result-list--hide')
      }
    }
  }
}

function toggleList() {
  showAll.value = !showAll.value
  void nextTick(() => {
    applyShowAll()
  })
}

onMounted(() => {
  if (props.useShowAll) {
    applyShowAll()
  }
})
</script>

<template>
  <ul ref="result-list" class="unified-search-result-list">
    <slot />
  </ul>
  <button v-if="useShowAll" class="unified-search-result-list__show-all" @click="toggleList">
    <span
      class="unified-search-result-list__chevron"
      :class="`unified-search-result-list__chevron--${showAll ? 'top' : 'right'}`"
    />
    {{ showAllBtnText }}
  </button>
</template>

<style scoped>
.unified-search-result-list {
  padding: 0;
  margin: 0;
  list-style-type: none;
  width: 100%;
  height: 100%;
  position: relative;
}

/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
:deep(.unified-search-result-list--hide) {
  display: none;
}

.unified-search-result-list__show-all {
  height: 20px;
  margin: 0;
  padding: 0;
  border: none;
  background: none;
  width: 100%;
  text-align: left;
  display: flex;
  align-items: center;

  &:hover {
    background-color: var(--ux-theme-5);
  }
}

.unified-search-result-list__chevron {
  display: inline-block;
  width: 8px;
  margin-right: var(--spacing);

  &::before {
    border-color: var(--success-dimmed);
    border-style: solid;
    border-width: 1px 1px 0 0;
    content: '';
    display: inline-block;
    width: 5px;
    height: 5px;
    position: relative;
    top: 4px;
    transform: rotate(-45deg);
    vertical-align: top;
  }

  &.unified-search-result-list__chevron--right {
    &::before {
      top: 3px;
      transform: rotate(45deg);
      transition: transform 100ms linear;
    }
  }

  &.unified-search-result-list__chevron--top::before {
    top: 6px;
    transform: rotate(-45deg);
    transition: transform 100ms linear;
  }
}
</style>
