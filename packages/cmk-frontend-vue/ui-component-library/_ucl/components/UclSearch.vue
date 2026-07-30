<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import { computed, ref, watch } from 'vue'

import { useNavigation } from '../composables/useNavigation'
import UclNavPage from './UclNavPage.vue'

const { allPages } = useNavigation()

const isSearching = defineModel<boolean>('isSearching', { default: false })

const searchQuery = ref('')

function clearSearch() {
  searchQuery.value = ''
}

const searchResults = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  return q ? allPages.filter((p) => p.name.toLowerCase().includes(q)) : null
})

watch(searchResults, (results) => {
  isSearching.value = results !== null
})
</script>

<template>
  <div class="ucl-search__input-wrapper">
    <div class="ucl-search__input-root">
      <CmkIcon class="ucl-search__input-icon" name="main-search" size="medium" />
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Search..."
        aria-label="Search components"
        class="ucl-search__input-field"
      />
    </div>
    <CmkIcon
      v-if="searchQuery.length > 0"
      class="ucl-search__input-reset"
      name="close"
      size="small"
      aria-label="Clear Search"
      @click.stop="clearSearch"
    />
  </div>

  <ul v-if="searchResults" class="ucl-search__results">
    <li v-for="page in searchResults" :key="page.path">
      <UclNavPage :page="page" />
    </li>
    <li v-if="searchResults.length === 0">No results found</li>
  </ul>
</template>

<style scoped>
.ucl-search__input-wrapper {
  display: flex;
  flex-direction: row;
  align-items: center;
  width: 95%;
  position: relative;
  margin-bottom: 12px;
}

.ucl-search__input-root {
  background-color: var(--default-form-element-bg-color);
  padding: 0 35px 0 0;
  width: 100%;
  border-radius: 2px;
  border: 1px solid var(--default-form-element-border-color);
  height: 24px;
  display: flex;
  align-items: center;

  &:focus-within {
    border: 1px solid var(--success);
  }
}

.ucl-search__input-icon {
  margin-left: var(--dimension-4, 8px);
}

.ucl-search__input-field {
  background: transparent;
  border: 0;
  width: 100%;
  height: 24px;
  padding: 0;
  margin-left: var(--dimension-4, 8px);
  color: var(--font-color);

  &::placeholder {
    color: var(--default-form-element-placeholder-color);
  }

  &:focus {
    outline: none;
  }
}

.ucl-search__input-reset {
  opacity: 0.6;
  cursor: pointer;
  position: absolute;
  right: 8px;

  &:hover {
    opacity: 1;
  }
}

.ucl-search__results {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
</style>
