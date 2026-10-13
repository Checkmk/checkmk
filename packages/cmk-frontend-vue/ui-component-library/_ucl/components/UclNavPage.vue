<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkTag from 'cmk-ui-library/components/CmkTag.vue'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import type { NavPage } from '../composables/useNavigation'
import { usePageStatus } from '../composables/usePageStatus'
import type { PageStatus } from '../types/page'

const { page } = defineProps<{
  page: NavPage
}>()

const { visibleStatus } = usePageStatus()

const statusLabel: Record<PageStatus, string> = {
  new: 'New',
  updated: 'Updated',
  deprecated: 'Deprecated'
}

const statusColor = {
  new: 'success',
  updated: 'warning',
  deprecated: 'danger'
} as const

const status = computed(() => visibleStatus(page))
</script>

<template>
  <RouterLink
    :to="page.path"
    class="ucl-nav-page"
    active-class="ucl-nav-page--active"
    exact-active-class="ucl-nav-page--active"
  >
    <span class="ucl-nav-page__name">{{ page.name }}</span>
    <CmkTag
      v-if="status"
      class="ucl-nav-page__status-chip"
      size="small"
      variant="fill"
      :color="statusColor[status]"
      :content="untranslated(statusLabel[status])"
    />
  </RouterLink>
</template>

<style scoped>
:root a.ucl-nav-page {
  display: flex;
  align-items: center;
  gap: var(--dimension-3, 6px);
  font-size: var(--ucl-font-size-body);
  padding: 6px 0 6px 20px;
  text-decoration: none;
  cursor: pointer;
  color: var(--ucl-body-text-color);
}

.ucl-nav-page__name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ucl-nav-page__status-chip {
  flex: none;
  margin: 0;
}

:root a.ucl-nav-page.ucl-nav-page--active {
  color: var(--ucl-nav-tree-link-active-color);
  font-weight: 700;
  border-left: 3px solid var(--ucl-nav-tree-link-active-color);
  background-color: var(--ucl-nav-tree-link-active-color-bg);
  padding: 6px 0 6px 17px;
}
</style>
