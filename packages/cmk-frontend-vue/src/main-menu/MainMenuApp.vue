<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { type MainMenuConfig, type NavItemIdEnum } from 'cmk-shared-typing/typescript/main_menu'
import { provide, ref } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'
import { KeyShortcutService } from '@/lib/keyShortcuts'

import CmkButton from '@/components/CmkButton'
import CmkKeyboardKey from '@/components/CmkKeyboardKey.vue'
import CmkPopupDialog from '@/components/CmkPopupDialog.vue'

import { MainMenuService } from '@/main-menu/lib/main-menu-service'
import { type UserPopupMessageRef } from '@/main-menu/lib/type-defs'

import NavItem from './components/NavItem.vue'
import SidebarToggle from './components/SidebarToggle.vue'
import ItemPopup from './components/popup/ItemPopup.vue'
import PopupBackdrop from './components/popup/PopupBackdrop.vue'
import { mainMenuKey } from './provider/main-menu'

const { _t } = usei18n()
const props = defineProps<MainMenuConfig>()
const iFrames = document.getElementsByTagName('iframe')
const mainMenu = new MainMenuService(
  props.main,
  props.user,
  new KeyShortcutService(window, iFrames, iFrames)
)
provide(mainMenuKey, mainMenu)

const usePopupMessages = ref<UserPopupMessageRef[]>([])

function onClick(id: NavItemIdEnum) {
  if (mainMenu.isNavItemActive(id)) {
    mainMenu.close()
  } else {
    mainMenu.navigate(id)
  }
}

mainMenu.onUserPopupMessages((msgs) => {
  usePopupMessages.value = msgs
})

function navElClick(e: MouseEvent) {
  if (e.target instanceof HTMLUListElement) {
    if (e.target.id === 'main-menu') {
      mainMenu.close()
    }
  }
}
</script>

<template>
  <nav :class="{ 'mm-app--small': props.hide_item_title }" @click="navElClick">
    <a id="home" :href="props.start.url || '/'" :title="props.start.title" target="_self">
      <img
        :src="
          props.start.icon_path || props.hide_item_title
            ? 'themes/facelift/images/icon_checkmk_logo_min.svg'
            : 'themes/facelift/images/icon_checkmk_logo.svg'
        "
      />
    </a>
    <ul id="main-menu">
      <NavItem
        v-for="item in props.main"
        :key="`nav-item-${item.id}`"
        :item="item"
        :hide-item-title="props.hide_item_title"
        :active="mainMenu.isNavItemActive(item.id)"
        @click.stop="onClick(item.id)"
      />
      <div class="mm-app__key-hint-wrapper">
        <CmkButton
          :variant="mainMenu.showKeyHints.value ? 'success' : 'optional'"
          class="mm-app__key-hint-button"
          @click="mainMenu.toggleKeyHints()"
        >
          {{ _t('Key hints') }}
        </CmkButton>
        <CmkKeyboardKey
          v-if="mainMenu.showKeyHints.value"
          :keyboard-key="_t('Alt + k')"
          size="small"
          class="mm-app__key-hint"
        />
      </div>
    </ul>
    <ul id="user-menu">
      <NavItem
        v-for="item in props.user"
        :key="item.id"
        :item="item"
        :hide-item-title="props.hide_item_title"
        :active="mainMenu.isNavItemActive(item.id)"
        @click.stop="onClick(item.id)"
      />
      <SidebarToggle :hide-item-title="props.hide_item_title" />
    </ul>
    <template
      v-for="item in props.main.concat(props.user).filter((i) => i.type === 'item')"
      :key="`nav-popup-${item.id}`"
    >
      <PopupBackdrop v-show="mainMenu.isNavItemActive(item.id)">
        <ItemPopup :item="item" :active="mainMenu.isNavItemActive(item.id)" />
      </PopupBackdrop>
    </template>
  </nav>
  <CmkPopupDialog
    v-for="msg in usePopupMessages"
    :key="msg.id"
    :open="msg.open"
    :title="msg.title as TranslatedString"
    :text="msg.text as TranslatedString"
    @close="
      () => {
        mainMenu.markMessageRead(msg.id)
        msg.open = false
      }
    "
  />
</template>

<style scoped>
nav {
  display: flex;
  flex-direction: column;
  float: left;
  width: 64px;
  height: 100%;
  position: fixed;
  background: var(--default-nav-bg-color);
  left: 0;
  top: 0;

  #home {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 58px;
    width: 100%;

    img {
      width: 48px;
      height: 48px;
    }
  }

  &.mm-app--small {
    width: 48px;

    #home {
      img {
        width: 28px;
        height: 28px;
      }
    }
  }

  ul {
    padding: 0;
    margin: 0;
    list-style: none;
    display: flex;
    flex-direction: column;
    align-items: center;

    &#main-menu {
      flex-grow: 1;
    }

    .mm-app__key-hint-wrapper {
      position: relative;

      .mm-app__key-hint-button {
        margin: var(--dimension-3);
        margin-top: var(--spacing-double);
        font-size: var(--font-size-small);
        font-weight: var(--font-weight-default);
        padding: var(--dimension-3);
      }

      .mm-app__key-hint {
        position: absolute;
        left: 45px;
        top: 28px;
        white-space: nowrap;
        z-index: +1;
      }
    }
  }
}
</style>
