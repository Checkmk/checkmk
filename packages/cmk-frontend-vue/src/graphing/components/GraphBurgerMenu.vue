<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon/CmkIcon.vue'
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import CmkSpace from 'cmk-ui-library/components/CmkSpace.vue'
import { onUnmounted, ref, watch } from 'vue'

import type { BurgerMenuCallable, BurgerMenuGroup } from '../types'
import { BOTTOM_SCREEN_MARGIN } from './constants'

const props = withDefaults(defineProps<{ groups?: BurgerMenuGroup[]; scrollable?: boolean }>(), {
  groups: () => [],
  scrollable: true
})

const emit = defineEmits<{ doAction: [onClick: BurgerMenuCallable] }>()

const isOpen = ref(false)
const containerRef = ref<HTMLElement | null>(null)
const dropdownMaxHeight = ref<number | null>(null)

function onDocumentClick(e: MouseEvent) {
  if (containerRef.value && !containerRef.value.contains(e.target as Node)) {
    isOpen.value = false
  }
}

function updateDropdownMaxHeight() {
  if (!props.scrollable || !containerRef.value) {
    dropdownMaxHeight.value = null
    return
  }
  dropdownMaxHeight.value =
    window.innerHeight - containerRef.value.getBoundingClientRect().bottom - BOTTOM_SCREEN_MARGIN
}

watch(isOpen, (open) => {
  if (open) {
    updateDropdownMaxHeight()
    window.addEventListener('resize', updateDropdownMaxHeight)
  } else {
    window.removeEventListener('resize', updateDropdownMaxHeight)
  }
})

document.addEventListener('click', onDocumentClick)
onUnmounted(() => {
  document.removeEventListener('click', onDocumentClick)
  window.removeEventListener('resize', updateDropdownMaxHeight)
})

function doAction(onClick: BurgerMenuCallable) {
  emit('doAction', onClick)
  isOpen.value = false
}
</script>

<template>
  <div ref="containerRef" class="graphing-graph-burger-menu">
    <button
      class="graphing-graph-burger-menu__trigger"
      :class="{ 'graphing-graph-burger-menu__trigger_open': isOpen }"
      :aria-expanded="isOpen"
      tabindex="0"
      @click="isOpen = !isOpen"
    >
      <CmkMultitoneIcon name="burger-menu" primary-color="font" size="small" />
    </button>

    <div
      v-if="isOpen"
      class="graphing-graph-burger-menu__dropdown"
      :class="{ 'graphing-graph-burger-menu__dropdown_scrollable': scrollable }"
      :style="
        scrollable && dropdownMaxHeight !== null
          ? { maxHeight: `${dropdownMaxHeight}px` }
          : undefined
      "
    >
      <ul
        v-for="group in groups"
        :key="group.heading"
        class="graphing-graph-burger-menu__group"
        :aria-label="group.heading"
      >
        <li class="graphing-graph-burger-menu__group-heading" aria-hidden="true">
          {{ group.heading }}
        </li>
        <li
          v-for="action in group.actions"
          :key="action.label"
          class="graphing-graph-burger-menu__item"
        >
          <button
            :aria-label="action.label"
            class="graphing-graph-burger-menu__item-button"
            @click="doAction(action.onClick)"
          >
            <template v-if="action.icon">
              <CmkIcon :name="action.icon" size="small" />
              <CmkSpace size="small" />
            </template>
            <span class="graphing-graph-burger-menu__item-label">{{ action.label }}</span>
          </button>
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped lang="scss">
.graphing-graph-burger-menu {
  position: relative;
}

.graphing-graph-burger-menu__trigger {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  border: var(--dimension-1) solid var(--button-form-border-color);
  border-radius: var(--border-radius);
  background: var(--color-midnight-grey-100);
  font-size: 16px;
  cursor: pointer;
  color: inherit;
  opacity: 0.7;

  &:hover {
    opacity: 1;
    background: rgb(0 0 0 / 6%);
  }
}

.graphing-graph-burger-menu__trigger_open {
  border-radius: var(--border-radius) var(--border-radius) 0 var(--border-radius);
}

.graphing-graph-burger-menu__dropdown {
  position: absolute;
  top: calc(100% - 1px);
  right: 10px;
  z-index: 100;
  min-width: 200px;
  border-radius: var(--border-radius) 0 var(--border-radius) var(--border-radius);
  border: var(--dimension-1) solid var(--button-form-border-color);
  background-color: var(--ux-theme-5);
  color: var(--font-color);
  font-size: var(--font-size-normal);
  font-weight: var(--font-weight-default);
  white-space: nowrap;
  padding: var(--dimension-4);
  box-shadow:
    0 2px 8px rgb(0 0 0 / 12%),
    0 0 0 1px rgb(0 0 0 / 6%);
}

.graphing-graph-burger-menu__dropdown_scrollable {
  overflow-y: auto;
}

.graphing-graph-burger-menu__group {
  list-style-type: none;
  padding-left: 0 !important;
  margin: 0;
  &:not(:last-child) {
    padding-bottom: var(--dimension-6);
  }
}

.graphing-graph-burger-menu__group-heading {
  font-weight: var(--font-weight-bold);
  padding-bottom: var(--dimension-4);
}

.graphing-graph-burger-menu__item {
  padding-bottom: var(--dimension-3);
  &:hover {
    color: var(--default-select-hover-color);
  }
}

.graphing-graph-burger-menu__item-button {
  display: flex;
  align-items: center;
  width: 100%;
  padding: 0;
  border: none;
  margin: 0;
  background: none;
  color: inherit;
  font-size: inherit;
}

body[data-theme='facelift'] {
  .graphing-graph-burger-menu__trigger {
    background-color: var(--color-daylight-grey-50);
  }
}
</style>
