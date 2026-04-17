<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { NavItemIdEnum, NavItemTopicEntry } from 'cmk-shared-typing/typescript/main_menu'

import type { TranslatedString } from '@/lib/i18nString'

import CmkDynamicIcon from '@/components/CmkIcon/CmkDynamicIcon/CmkDynamicIcon.vue'
import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'
import CmkTag from '@/components/CmkTag.vue'

import { getInjectedMainMenu } from '@/main-menu/provider/main-menu'

const mainMenu = getInjectedMainMenu()

defineProps<{
  entry: NavItemTopicEntry
  navItemId: NavItemIdEnum
}>()
</script>

<template>
  <a :href="entry.url || 'javascript:void(0)'" :target="entry.target || 'main'">
    <span v-if="entry.icon" class="mm-nav-item-topic-entry-link__icon">
      <CmkDynamicIcon :spec="entry.icon" />
    </span>
    <span>{{ entry.title }}</span>

    <span v-if="entry.mode === 'multilevel'" class="mm-nav-item-topic-entry-link__chevron" />
    <CmkIcon
      v-else-if="entry.url && entry.target === '_blank'"
      class="mm-nav-item-topic-entry-link__external-link"
      name="external"
      size="small"
    />

    <div
      v-if="entry.chip && mainMenu.chipEntry(entry.chip.mode)"
      class="mm-nav-item-topic-entry-link__toggle-chip"
    >
      <CmkTag
        :content="mainMenu.chipEntry(entry.chip.mode) as TranslatedString"
        :color="entry.chip.color || 'default'"
        variant="fill"
        size="small"
      />
    </div>
    <div v-if="entry.toggle" class="mm-nav-item-topic-entry-link__toggle-button">
      <CmkTag
        :content="entry.toggle.value as TranslatedString"
        :color="entry.toggle.color || 'default'"
        variant="fill"
        size="small"
        class="mm-nav-item-topic-entry-link__toggle-button-chip"
      />
    </div>
  </a>
</template>

<style scoped>
a {
  text-decoration: none;
  line-height: 22px;
  display: flex;
  align-items: center;
  width: 100%;

  &:hover {
    color: var(--success);
  }

  .mm-nav-item-topic-entry-link__icon {
    width: 18px;
    height: 14px;
    position: absolute;
    margin-left: -23px;
    display: flex;
    align-items: center;

    .mm-nav-item-topic-entry-link__icon-emblem {
      position: absolute;
      bottom: -2px;
      right: -2px;
    }
  }

  .mm-nav-item-topic-entry-link__external-link {
    position: relative;
    opacity: 0.5;
    margin-left: var(--dimension-4);
  }

  .mm-nav-item-topic-entry-link__chevron {
    position: relative;
    margin-left: var(--dimension-4);

    &::after {
      border-color: var(--font-color);
      border-style: solid;
      border-width: 1px 1px 0 0;
      content: '';
      display: inline-block;
      width: 5px;
      height: 5px;
      position: relative;
      transform: rotate(45deg);
      top: -1px;
      vertical-align: middle;
    }
  }

  .mm-nav-item-topic-entry-link__toggle-chip {
    text-align: left;
  }

  .mm-nav-item-topic-entry-link__toggle-button {
    flex-grow: 1;
    text-align: right;

    .mm-nav-item-topic-entry-link__toggle-button-chip {
      display: inline-flex;
      min-width: 50px;
      box-sizing: border-box;
      height: 16px;
      align-items: center;
      justify-content: center;
    }
  }
}
</style>
