<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed } from 'vue'

import CmkIcon from '@/components/CmkIcon'

import type { NavFolder } from '../composables/useNavigation'
import UclNavPage from './UclNavPage.vue'

const { folder, isRoot = false } = defineProps<{
  folder: NavFolder
  isRoot?: boolean
}>()

const isOpen = computed(() => folder.isOpen.value)

function toggle(f: NavFolder) {
  f.isOpen.value = !f.isOpen.value
}
</script>

<template>
  <button
    class="ucl-nav-folder"
    :class="{ 'ucl-nav-folder--root': isRoot }"
    :aria-expanded="isOpen"
    @click="toggle(folder)"
  >
    <CmkIcon name="tree-closed" size="xxsmall" :rotate="isOpen ? 90 : 0" aria-hidden="true" />
    {{ folder.name }}
  </button>

  <ul v-if="isOpen" class="ucl-nav-folder__children">
    <li v-for="child in folder.children" :key="child.path">
      <UclNavFolder v-if="child.type === 'folder'" :folder="child" />
      <UclNavPage v-else :page="child" />
    </li>
  </ul>
</template>

<style scoped>
.ucl-nav-folder {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  background: none;
  border: none;
  padding: 4px 0 4px 8px;
  font-size: 12px;
  text-decoration: none;
  cursor: pointer;
  color: var(--ucl-headings-font-color);
  font-weight: 700;
}

.ucl-nav-folder:focus-visible {
  outline: revert;
}

.ucl-nav-folder--root {
  font-size: 14px;
  padding: 8px 0;
}

.ucl-nav-folder__children {
  margin-left: 15px;
  list-style: none;
  padding: 0;
  margin-top: 4px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
</style>
