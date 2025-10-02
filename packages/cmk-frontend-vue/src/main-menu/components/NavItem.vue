<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { NavItem } from 'cmk-shared-typing/typescript/main_menu'
import { computed } from 'vue'

import CmkBadge from '@/components/CmkBadge.vue'
import CmkMultitoneIcon from '@/components/CmkIcon/CmkMultitoneIcon.vue'
import type { CmkMultitoneIconColor, OneColorIcons } from '@/components/CmkIcon/types'
import CmkKeyboardKey from '@/components/CmkKeyboardKey.vue'

import { getInjectedMainMenu } from '../provider/main-menu'

const mainMenu = getInjectedMainMenu()

const props = defineProps<{
  active?: boolean | undefined
  item: NavItem
}>()

const color = computed<CmkMultitoneIconColor>(() => {
  return (props.active ? 'success' : 'font') as CmkMultitoneIconColor
})

const icon = computed<OneColorIcons>(() => {
  return props.item.id as OneColorIcons
})
</script>

<template>
  <li
    :id="`nav-item-${item.id}`"
    class="mm-nav-item__li"
    :class="{ 'mm-nav-item__li--active': active }"
  >
    <a href="javascript:void(0)">
      <CmkMultitoneIcon
        :name="icon"
        :primary-color="color"
        size="xlarge"
        class="mm-nav-item__icon"
      />
      <CmkKeyboardKey
        v-if="mainMenu.showKeyHints.value && props.item.shortcut"
        :keyboard-key="mainMenu.getNavShortCutInfo(props.item.shortcut)"
        size="small"
        class="mm-nav-item__key-hint"
      />
      <CmkBadge
        v-if="mainMenu.getNavItemBadge(item.id)"
        class="mm-nav-item__badge"
        size="small"
        :color="mainMenu.getNavItemBadge(item.id)?.color"
        >{{ mainMenu.getNavItemBadge(item.id)?.content }}</CmkBadge
      >
      <span>{{ item.title }}</span>
    </a>
  </li>
</template>
<style scoped>
.mm-nav-item__li {
  width: 100%;
  height: 60px;
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

    .mm-nav-item__icon {
      margin-bottom: var(--dimension-4);
    }

    .mm-nav-item__key-hint {
      position: absolute;
      left: 35px;
      white-space: nowrap;
      z-index: +1;
    }

    .mm-nav-item__badge {
      position: absolute;
      top: var(--dimension-3);
      right: var(--dimension-3);
      padding: 0;
      margin: 0;
    }
  }

  &.mm-nav-item__li--active {
    border-left-color: var(--success);
    background-color: var(--ux-theme-1);

    a {
      color: var(--success);
    }
  }
}
</style>
