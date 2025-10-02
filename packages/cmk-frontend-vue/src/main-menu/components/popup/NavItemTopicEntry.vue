<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { NavItemIdEnum, NavItemTopicEntry } from 'cmk-shared-typing/typescript/main_menu'

import type { TranslatedString } from '@/lib/i18nString'

import CmkChip from '@/components/CmkChip.vue'
import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'

import { getInjectedMainMenu } from '../../provider/main-menu'

const mainMenu = getInjectedMainMenu()

defineProps<{
  entry: NavItemTopicEntry
  navItemId: NavItemIdEnum
}>()

function clickLi(entry: NavItemTopicEntry) {
  if (entry.toggle) {
    void mainMenu.toggleEntry(entry.toggle.mode, entry.toggle.reload)
  }
}
</script>

<template>
  <li ref="topic-entries" @click="clickLi(entry)">
    <a :href="entry.url || 'javascript:void(0)'" :target="entry.target || 'main'">
      <img v-if="entry.icon" :src="entry.icon" width="18" height="14" />
      {{ entry.title }}

      <CmkIcon
        v-if="entry.url && entry.target === '_blank'"
        class="mm-nav-item-topic-entry__external-link"
        name="external"
        size="small"
      />
      <div
        v-if="entry.chip && mainMenu.chipEntry(entry.chip.mode)"
        class="mm-nav-item-topic-entry__chip"
      >
        <CmkChip
          :content="mainMenu.chipEntry(entry.chip.mode) as TranslatedString"
          :color="entry.chip.color || 'default'"
          variant="fill"
          size="small"
        />
      </div>
      <div v-if="entry.toggle" class="mm-nav-item-topic-entry__toggle-button">
        <CmkChip
          :content="entry.toggle.value as TranslatedString"
          :color="entry.toggle.color || 'default'"
          variant="fill"
          size="small"
        />
      </div>
    </a>
  </li>
</template>

<style scoped>
li {
  list-style-type: none;
  margin-left: 26px;
  display: flex;
  align-items: center;

  a {
    text-decoration: none;
    line-height: 22px;
    display: flex;
    align-items: center;
    width: 100%;

    &:hover {
      color: var(--success);
    }

    img {
      position: absolute;
      margin-left: -23px;
    }

    .mm-nav-item-topic-entry__external-link {
      position: relative;
      opacity: 0.5;
      margin-left: var(--dimension-4);
    }

    .mm-nav-item-topic-entry__toggle-chip {
      text-align: left;
    }

    .mm-nav-item-topic-entry__toggle-button {
      flex-grow: 1;
      text-align: right;
    }
  }
}
</style>
