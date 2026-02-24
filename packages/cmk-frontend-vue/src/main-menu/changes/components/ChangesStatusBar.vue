<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkMultitoneIcon from '@/components/CmkIcon/CmkMultitoneIcon.vue'

import { getInjectedMainMenu } from '@/main-menu/provider/main-menu'

const props = defineProps<{
  activateChangesUrl: string
  pendingChanges: number
  activationIssues: number
  siteProblems: number
}>()
const { _t } = usei18n()
const mainMenu = getInjectedMainMenu()

function handleClick(event: MouseEvent) {
  // Ignore right-click and ctrl/cmd-click for opening in new tab
  if (event.button !== 0 || event.ctrlKey || event.metaKey) {
    return
  }

  event.preventDefault()
  mainMenu.close()
  window.open(props.activateChangesUrl, 'main')
}
</script>

<template>
  <a :href="activateChangesUrl" target="main" class="mm-changes-status-bar" @click="handleClick">
    <div class="mm-changes-status-bar__item">
      <span class="mm-changes-status-bar__icon-with-count">
        <CmkMultitoneIcon
          v-if="pendingChanges === 0"
          name="success"
          primary-color="success"
          size="small"
        />
        {{ pendingChanges }}
      </span>
      <span>{{ _t('Pending change(s)') }}</span>
    </div>
    <div class="mm-changes-status-bar__item">
      <span class="mm-changes-status-bar__icon-with-count">
        <CmkMultitoneIcon
          :name="activationIssues ? 'warning' : 'success'"
          :primary-color="activationIssues ? 'warning' : 'success'"
          size="small"
        />
        {{ activationIssues }}
      </span>
      <span>{{ _t('Activation issue(s)') }}</span>
    </div>
    <div class="mm-changes-status-bar__item">
      <span class="mm-changes-status-bar__icon-with-count">
        <CmkMultitoneIcon
          :name="siteProblems ? 'error' : 'success'"
          :primary-color="siteProblems ? 'danger' : 'success'"
          size="small"
        />
        {{ siteProblems }}
      </span>
      <span>{{ _t('Site problem(s)') }}</span>
    </div>
  </a>
</template>

<style scoped>
.mm-changes-status-bar {
  display: flex;
  width: 100%;
  justify-content: space-between;
  align-items: center;
  border-radius: var(--dimension-3);
  border: 1px solid var(--default-form-element-border-color);
  background: var(--ux-theme-0);
  cursor: pointer;
  text-decoration: none;
}

.mm-changes-status-bar:hover {
  background: var(--ux-theme-3);
}

.mm-changes-status-bar__item {
  display: flex;
  padding: var(--dimension-5);
  flex: 1;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: var(--dimension-2);
}

.mm-changes-status-bar__item:not(:last-child) {
  border-right: 1px solid var(--default-form-element-border-color);
}

.mm-changes-status-bar__icon-with-count {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
}
</style>
