<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { onUnmounted, ref } from 'vue'

import CmkMultitoneIcon from '@/components/CmkIcon/CmkMultitoneIcon.vue'

import type { BurgerMenuGroup } from '../types'

withDefaults(defineProps<{ groups?: BurgerMenuGroup[] }>(), { groups: () => [] })

const isOpen = ref(false)
const containerRef = ref<HTMLElement | null>(null)

function onDocumentClick(e: MouseEvent) {
  if (containerRef.value && !containerRef.value.contains(e.target as Node)) {
    isOpen.value = false
  }
}

document.addEventListener('click', onDocumentClick)
onUnmounted(() => document.removeEventListener('click', onDocumentClick))

function doAction(onClick: () => void) {
  onClick()
  isOpen.value = false
}
</script>

<template>
  <div ref="containerRef" class="graphing-graph-burger-menu">
    <button class="graphing-graph-burger-menu__trigger" @click="isOpen = !isOpen">
      <CmkMultitoneIcon name="burger-menu" primary-color="font" size="small" />
    </button>

    <div v-if="isOpen" class="graphing-graph-burger-menu__dropdown">
      <template v-for="(group, i) in groups" :key="group.heading">
        <div v-if="i > 0" role="separator" class="graphing-graph-burger-menu__separator" />
        <div class="graphing-graph-burger-menu__group-heading">{{ group.heading }}</div>
        <button
          v-for="action in group.actions"
          :key="action.label"
          class="graphing-graph-burger-menu__item"
          @click="doAction(action.onClick)"
        >
          {{ action.label }}
        </button>
      </template>
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
  border: none;
  border-radius: var(--border-radius);
  background: transparent;
  font-size: 16px;
  cursor: pointer;
  color: inherit;
  opacity: 0.7;

  &:hover {
    opacity: 1;
    background: rgb(0 0 0 / 6%);
  }
}

.graphing-graph-burger-menu__dropdown {
  position: absolute;
  top: calc(100% + 4px);
  right: 0;
  z-index: 100;
  min-width: 200px;
  padding: 6px 0;
  background: #fff;
  border-radius: var(--border-radius);
  box-shadow:
    0 2px 8px rgb(0 0 0 / 12%),
    0 0 0 1px rgb(0 0 0 / 6%);
}

.graphing-graph-burger-menu__separator {
  height: 1px;
  margin: 6px 0;
  background: #f0f0f0;
}

.graphing-graph-burger-menu__group-heading {
  padding: 6px 14px 2px;
  font-size: var(--font-size-small);
  font-weight: var(--font-weight-bold);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  opacity: 0.5;
}

.graphing-graph-burger-menu__item {
  display: block;
  width: 100%;
  padding: 5px 14px;
  border: none;
  background: transparent;
  font-size: var(--font-size-normal);
  text-align: left;
  cursor: pointer;
  color: inherit;

  &:hover {
    background: #f5f5f5;
  }
}
</style>
