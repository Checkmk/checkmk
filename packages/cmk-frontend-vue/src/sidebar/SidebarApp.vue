<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { type SidebarConfig } from 'cmk-shared-typing/typescript/sidebar'
import { provide } from 'vue'

import usei18n from '@/lib/i18n'
import { KeyShortcutService } from '@/lib/keyShortcuts'
import { SidebarService } from '@/lib/sidebar/sidebar'

import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'
import CmkScrollContainer from '@/components/CmkScrollContainer.vue'

import SidebarSnapin from './components/snapin/SidebarSnapin.vue'
import { sidebarKey } from './provider/sidebar'

const { _t } = usei18n()
const props = defineProps<SidebarConfig>()

const sidebar = new SidebarService(props.snapins, new KeyShortcutService(window))
provide(sidebarKey, sidebar)
</script>

<template>
  <div class="sidebar-app__wrapper">
    <CmkScrollContainer
      class="sidebar-app__snapin-container"
      max-height="calc(100vh - 50px)"
      type="outer"
    >
      <SidebarSnapin
        v-for="snapin in props.snapins"
        :key="snapin.name"
        class="sidebar-app__snapin"
        v-bind="snapin"
      />
    </CmkScrollContainer>
    <div class="sidebar-app__add-snapin">
      <a href="sidebar_add_snapin.py" :title="_t('Add elements to your sidebar')">
        <CmkIcon name="add" size="xlarge" />
      </a>
    </div>
  </div>
</template>

<style scoped>
.sidebar-app__wrapper {
  width: 280px;
  height: 100vh;
  background: var(--default-nav-bg-color);
  display: flex;
  flex-direction: column;

  .sidebar-app__snapin-container {
    flex-grow: 1;
    display: flex;
    flex-direction: column;
  }

  .sidebar-app__snapin:first-of-type {
    margin-top: var(--dimension-3);
  }

  .sidebar-app__add-snapin {
    display: flex;
    flex-direction: column;
    align-items: center;
    height: var(--dimension-8);
    width: 100%;

    a {
      display: flex;
      flex-direction: column;
      align-items: center;
      width: 100%;
      box-sizing: border-box;
      padding: var(--dimension-5);

      img {
        opacity: 0.5;
      }
    }
  }
}
</style>
