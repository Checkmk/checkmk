<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { type MainMenuConfig } from 'cmk-shared-typing/typescript/main_menu'
import { provide, ref } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'
import { KeyShortcutService } from '@/lib/keyShortcuts'
import { MainMenuService } from '@/lib/main-menu/service/main-menu'
import { type UserPopupMessageRef } from '@/lib/main-menu/service/type-defs'

import CmkButton from '@/components/CmkButton.vue'
import CmkKeyboardKey from '@/components/CmkKeyboardKey.vue'
import CmkPopupDialog from '@/components/CmkPopupDialog.vue'

import NavItem from './components/NavItem.vue'
import ItemPopup from './components/popup/ItemPopup.vue'
import PopupBackdrop from './components/popup/PopupBackdrop.vue'
import { mainMenuKey } from './provider/main-menu'

const { _t } = usei18n()
const props = defineProps<MainMenuConfig>()

const mainMenu = new MainMenuService(props.main, props.user, new KeyShortcutService(window))
provide(mainMenuKey, mainMenu)

const usePopupMessages = ref<UserPopupMessageRef[]>([])

mainMenu.onUserPopupMessages((msgs) => {
  usePopupMessages.value = msgs
})
</script>

<template>
  <nav>
    <a id="home" :href="props.start.url || '/'" :title="props.start.title">
      <img :src="props.start.icon || 'themes/facelift/images/icon_checkmk_logo.svg'" />
    </a>
    <ul id="main-menu">
      <NavItem
        v-for="item in props.main"
        :key="`nav-item-${item.id}`"
        :item="item"
        :active="mainMenu.isNavItemActive(item.id)"
        @click="mainMenu.navigate(item.id)"
        @mouseover="mainMenu.navigateIfAnyNavItemIsActive(item.id)"
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
          keyboard-key="Alt"
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
        :active="mainMenu.isNavItemActive(item.id)"
        @click="mainMenu.navigate(item.id)"
        @mouseover="mainMenu.navigateIfAnyNavItemIsActive(item.id)"
      />
    </ul>
    <PopupBackdrop v-if="mainMenu.isAnyNavItemActive()">
      <template v-for="item in props.main.concat(props.user)">
        <ItemPopup
          v-if="mainMenu.isNavItemActive(item.id)"
          :key="`nav-popup-${item.id}`"
          :item="item"
          @click.stop
        />
      </template>
    </PopupBackdrop>
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
