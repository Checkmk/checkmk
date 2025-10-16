<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { NavItemShortcut } from 'cmk-shared-typing/typescript/main_menu'
import { computed } from 'vue'

import usei18n from '@/lib/i18n'
import { SidebarService } from '@/lib/sidebar/sidebar'

import CmkMultitoneIcon from '@/components/CmkIcon/CmkMultitoneIcon.vue'
import type { CmkMultitoneIconColor } from '@/components/CmkIcon/types'
import CmkKeyboardKey from '@/components/CmkKeyboardKey.vue'

import { getInjectedMainMenu } from '../provider/main-menu'

const { _t } = usei18n()
const mainMenu = getInjectedMainMenu()

const shortCut: NavItemShortcut = {
  key: '/',
  ctrl: true
}

const color = computed<CmkMultitoneIconColor>(() => {
  return (SidebarService.isActive() ? 'success' : 'font') as CmkMultitoneIconColor
})
</script>

<template>
  <li
    id="nav-item-sidebar"
    class="mm-sidebar-toggle__li"
    :class="{ 'mm-sidebar-toggle__li--active': SidebarService.isActive() }"
  >
    <a href="javascript:void(0)" @click="SidebarService.toggle()">
      <CmkMultitoneIcon
        name="sidebar"
        :primary-color="color"
        size="large"
        class="mm-sidebar-toggle__icon"
      />
      <CmkKeyboardKey
        v-if="mainMenu.showKeyHints.value"
        :keyboard-key="mainMenu.getNavShortCutInfo(shortCut)"
        size="small"
        class="mm-sidebar-toggle__key-hint"
      />
      <span>{{ _t('Sidebar') }}</span>
    </a>
  </li>
</template>
<style scoped>
.mm-sidebar-toggle__li {
  width: 100%;
  height: 56px;
  border-left: var(--dimension-3) solid transparent;
  font-size: var(--font-size-small);
  display: flex;
  box-sizing: border-box;

  &:hover {
    border-left-color: var(--success);
  }

  a {
    position: relative;
    height: 100%;
    width: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-decoration: none;
    padding-right: 4px;

    .mm-sidebar-toggle__icon {
      margin-bottom: var(--dimension-4);
    }

    .mm-sidebar-toggle__key-hint {
      position: absolute;
      left: 35px;
      white-space: nowrap;
      z-index: +1;
    }
  }

  &.mm-sidebar-toggle__li--active {
    a {
      color: var(--success);
    }
  }
}
</style>
