<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { nextTick, ref } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'
import useClickOutside from '@/lib/useClickOutside'

import ArrowDown from '@/components/graphics/ArrowDown.vue'

import MenuButton from './MenuButton.vue'

const { label } = defineProps<{ label: TranslatedString }>()

const vClickOutside = useClickOutside()

const menuShown = ref(false)
const menuRef = ref<HTMLDivElement | null>(null)

function showMenu(): void {
  menuShown.value = !menuShown.value
  if (!menuShown.value) {
    return
  }
  // eslint-disable-next-line @typescript-eslint/no-floating-promises
  nextTick(async () => {
    if (menuRef.value) {
      const menuRect = menuRef.value.getBoundingClientRect()
      if (window.innerHeight - menuRect.bottom < menuRect.height) {
        menuRef.value.style.bottom = `calc(2 * var(--spacing))`
      } else {
        menuRef.value.style.removeProperty('bottom')
      }
    }
  })
}

function hideMenu(): void {
  menuShown.value = false
}

defineExpose({
  hideMenu
})
</script>

<template>
  <div
    v-click-outside="
      () => {
        if (menuShown) menuShown = false
      }
    "
    class="cmk-dropdown-menu"
  >
    <MenuButton :aria-label="label" :aria-expanded="menuShown" @click="showMenu">
      <slot name="button" />
      <ArrowDown class="cmk-dropdown-menu--arrow" :class="{ rotated: menuShown }" />
    </MenuButton>

    <div v-if="menuShown" ref="menuRef" class="cmk-dropdown-menu--container">
      <div class="cmk-dropdown-menu--content">
        <slot name="menu" :hide-menu="hideMenu" />
      </div>
    </div>
  </div>
</template>

<style scoped>
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.cmk-dropdown-menu {
  display: inline-block;
  position: relative;
  white-space: nowrap;

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  .cmk-dropdown-menu--arrow {
    width: 0.7em;
    height: 0.7em;
    color: #888;
    margin: 0;
    flex-shrink: 0;

    /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
    &.rotated {
      transform: rotate(180deg);
    }
  }

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  .cmk-dropdown-menu--container {
    position: absolute;
    z-index: var(--z-index-dropdown);
    color: var(--font-color);
    background-color: var(--ux-theme-3);
    border: 1px solid var(--ux-theme-6);
    box-sizing: border-box;
    border-bottom-left-radius: var(--dimension-4);
    border-bottom-right-radius: var(--dimension-4);
    min-width: 200px;
    margin-top: 1px;
    width: max-content;
  }

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  .cmk-dropdown-menu--content {
    padding: 0;
    margin: 0;
  }
}
</style>
