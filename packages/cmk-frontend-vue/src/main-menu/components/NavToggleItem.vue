<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { NavToggleItem } from 'cmk-shared-typing/typescript/main_menu'
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import CmkKeyboardKey from 'cmk-ui-library/components/CmkKeyboardKey.vue'
import { computed, onBeforeUnmount } from 'vue'

import type { NavToggle } from '@/main-menu/lib/nav-toggles'
import { getInjectedMainMenu } from '@/main-menu/provider/main-menu'

const mainMenu = getInjectedMainMenu()

const props = defineProps<{
  item: NavToggleItem
  navToggle: NavToggle
  hideItemTitle: boolean
}>()

const unregisterShortcut = mainMenu.registerToggleShortcut(props.item, () =>
  props.navToggle.toggle()
)
onBeforeUnmount(unregisterShortcut)

const active = computed(() => props.navToggle.isActive())
</script>

<template>
  <li
    :id="`nav-item-${item.id}`"
    class="mm-nav-toggle-item__li"
    :class="{
      'mm-nav-toggle-item__li--active': active,
      'mm-nav-toggle-item__li--small': hideItemTitle,
      'mm-nav-toggle-item__li--highlight-ai': navToggle.highlight === 'ai'
    }"
    :title="item.hint || item.title"
  >
    <button type="button" :aria-pressed="active" @click="navToggle.toggle()">
      <CmkMultitoneIcon
        :name="navToggle.icon"
        :primary-color="{ custom: 'currentColor' }"
        size="large"
        class="mm-nav-toggle-item__icon"
      />
      <CmkKeyboardKey
        v-if="mainMenu.showKeyHints.value"
        :keyboard-key="mainMenu.getNavShortCutInfo(item.shortcut)"
        size="small"
        class="mm-nav-toggle-item__key-hint"
      />
      <span v-if="!hideItemTitle">{{ item.title }}</span>
    </button>
  </li>
</template>

<style scoped>
.mm-nav-toggle-item__li {
  width: 100%;
  height: 56px;
  border-left: var(--dimension-3) solid transparent;
  font-size: var(--font-size-small);
  display: flex;
  box-sizing: border-box;

  --mm-nav-toggle-item-active-color: var(--success);

  &.mm-nav-toggle-item__li--highlight-ai {
    --mm-nav-toggle-item-active-color: var(--ai-purple);
  }

  &:hover,
  &.mm-nav-toggle-item__li--active {
    border-left-color: var(--mm-nav-toggle-item-active-color);
  }

  button {
    position: relative;
    height: 100%;
    width: 100%;
    margin: 0;
    border: none;
    background: none;
    color: inherit;
    font: inherit;
    cursor: pointer;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-decoration: none;
    padding-right: 4px;

    .mm-nav-toggle-item__icon {
      margin-bottom: var(--dimension-4);
    }

    .mm-nav-toggle-item__key-hint {
      position: absolute;
      left: 35px;
      white-space: nowrap;
      z-index: +1;
    }
  }

  &.mm-nav-toggle-item__li--active button {
    color: var(--mm-nav-toggle-item-active-color);
  }

  &.mm-nav-toggle-item__li--small {
    height: 48px;

    .mm-nav-toggle-item__icon {
      margin-bottom: 0;
    }
  }
}
</style>
