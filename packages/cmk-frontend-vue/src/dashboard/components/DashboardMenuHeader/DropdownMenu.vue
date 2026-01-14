<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'

import type { SimpleIcons } from '@/components/CmkIcon'
import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'

import ButtonDropdownMenu from './ButtonDropdownMenu.vue'

interface DropdownMenuItemBase {
  label: TranslatedString
  icon?: SimpleIcons
  disabled?: boolean
  hidden?: boolean
}

interface DropdownMenuLinkOption extends DropdownMenuItemBase {
  url: string
  target?: '_blank' | '_self' | '_parent' | '_top' | string
}

interface DropdownMenuCallbackOption extends DropdownMenuItemBase {
  action: (() => void) | null
}

type DropdownMenuOption = DropdownMenuLinkOption | DropdownMenuCallbackOption

interface DropdownMenuProps {
  icon?: SimpleIcons
  label: TranslatedString
  options: DropdownMenuOption[]
  right?: boolean
  disabled?: boolean
}

const props = defineProps<DropdownMenuProps>()

const visibleOptions = computed(() => {
  return props.options.filter((option) => !option.hidden)
})
</script>

<template>
  <ButtonDropdownMenu :label="label" :right="!!right" :disabled="props.disabled">
    <template #button>
      <CmkIcon v-if="icon" :name="icon" size="large" />
      <span>{{ label }}</span>
    </template>
    <template #menu="{ hideMenu }">
      <div v-for="(option, index) in visibleOptions" :key="index" class="db-dropdown-menu__items">
        <!-- Link -->
        <a
          v-if="'url' in option"
          :href="option.url"
          :target="option.target || '_self'"
          class="db-dropdown-menu__item"
          @click="hideMenu()"
        >
          <div
            class="db-dropdown-menu__label db-dropdown-menu__no-underline"
            :class="option?.disabled ? 'db-dropdown-menu__label-disabled' : ''"
          >
            {{ option.label }}
            <CmkIcon v-if="option.icon" :name="option.icon" size="small" style="float: right" />
          </div>
        </a>

        <!-- Callback -->
        <div
          v-else
          class="db-dropdown-menu__item"
          :class="option?.disabled ? 'db-dropdown-menu__label-disabled' : ''"
          @click="
            () => {
              if (!option.disabled && option.action) {
                option.action()
              }

              hideMenu()
            }
          "
        >
          <div
            class="db-dropdown-menu__label"
            :class="option?.disabled ? 'db-dropdown-menu__label-disabled' : ''"
          >
            {{ option.label }}
            <CmkIcon v-if="option.icon" :name="option.icon" size="small" style="float: right" />
          </div>
        </div>
      </div>
    </template>
  </ButtonDropdownMenu>
</template>

<style scoped>
.db-dropdown-menu__items {
  width: 100%;

  .db-dropdown-menu__item {
    height: 40px;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    padding: var(--dimension-5) var(--dimension-6);
    margin-bottom: var(--dimension-3);
    border: none;
    background: none;
    color: var(--font-color);
    font-size: var(--font-size-normal);
    text-align: left;
    text-decoration: none;
    cursor: pointer;
    border-radius: var(--dimension-3);
    transition: background-color 0.2s ease;

    .db-dropdown-menu__label {
      color: var(--font-color);
      width: 100%;
    }

    &:last-child {
      margin-bottom: 0;
    }

    &:hover {
      background-color: var(--ux-theme-5);
    }

    .db-dropdown-menu__label-disabled {
      color: var(--menu-entry-disabled);
    }
  }
}

.db-dropdown-menu__no-underline {
  text-decoration: none !important;
}
</style>
