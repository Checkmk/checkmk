<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { RouterLink } from 'vue-router'

import type { NavPage } from '../composables/useNavigation'

const { page } = defineProps<{
  page: NavPage
}>()
</script>

<template>
  <RouterLink
    :to="page.path"
    class="ucl-nav-page"
    active-class="ucl-nav-page--active"
    exact-active-class="ucl-nav-page--active"
  >
    {{ page.name }}
  </RouterLink>
</template>

<style scoped>
:root a.ucl-nav-page {
  display: block;
  font-size: var(--ucl-font-size-body);
  padding: 6px 0 6px 20px;
  text-decoration: none;
  cursor: pointer;
  color: var(--ucl-body-text-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

:root a.ucl-nav-page.ucl-nav-page--active {
  color: var(--ucl-nav-tree-link-active-color);
  font-weight: 700;
  border-left: 3px solid var(--ucl-nav-tree-link-active-color);
  background-color: var(--ucl-nav-tree-link-active-color-bg);
  padding: 6px 0 6px 17px;
}
</style>
