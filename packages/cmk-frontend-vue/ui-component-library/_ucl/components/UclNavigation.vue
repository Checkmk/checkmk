<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'

import { useNavigation } from '../composables/useNavigation'
import UclNavFolder from './UclNavFolder.vue'
import UclSearch from './UclSearch.vue'

const { navTrees } = useNavigation()
const isSearching = ref(false)
</script>

<template>
  <UclSearch v-model:is-searching="isSearching" />

  <template v-if="!isSearching">
    <RouterLink
      to="/"
      class="ucl-navigation__home-link"
      active-class="ucl-navigation__home-link--active"
    >
      Home
    </RouterLink>

    <template v-for="navTree in navTrees" :key="navTree.path">
      <UclNavFolder :folder="navTree" :is-root="true" />
    </template>
  </template>
</template>

<style scoped>
.ucl-navigation__home-link {
  display: block;
  font-size: var(--ucl-font-size-body);
  font-weight: 700;
  color: var(--ucl-headings-font-color);
  padding: 4px 0 4px 26px;
  text-decoration: none;
}

.ucl-navigation__home-link.ucl-navigation__home-link--active {
  color: var(--ucl-nav-tree-link-active-color);
  border-left: 3px solid var(--ucl-nav-tree-link-active-color);
  background-color: var(--ucl-nav-tree-link-active-color-bg);
  padding-left: 23px;
}
</style>
