<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { NavItemIdEnum, NavItemTopicEntry } from 'cmk-shared-typing/typescript/main_menu'

import CmkHeading from '@/components/typography/CmkHeading.vue'

import { getInjectedMainMenu } from '@/main-menu/provider/main-menu'

import NavItemTopicEntryLink from './NavItemTopicEntryLink.vue'

const mainMenu = getInjectedMainMenu()

const props = defineProps<{
  entry: NavItemTopicEntry
  navItemId: NavItemIdEnum
}>()

function clickLi(entry: NavItemTopicEntry) {
  if (entry.toggle) {
    void mainMenu.toggleEntry(entry.toggle.mode, entry.toggle.reload)
    return
  }

  if (entry.mode === 'multilevel') {
    mainMenu.showAllEntriesOfTopic(props.navItemId, entry)
    return
  }

  mainMenu.close()
}
</script>

<template>
  <li @click="clickLi(entry)">
    <div v-if="entry.mode === 'indented'" class="mm-nav-item-topic-entry">
      <CmkHeading type="h4" class="mm-nav-item-topic-entry__indented-header">
        <span v-if="entry.icon" class="mm-nav-item-topic-entry__header-icon">
          <img :src="entry.icon.src" width="18" height="18" />
          <img
            v-if="entry.icon.emblem"
            class="mm-nav-item-topic-entry__icon-emblem"
            :src="entry.icon.emblem"
            width="10"
            height="10"
          />
        </span>
        <span>{{ entry.title }}</span>
      </CmkHeading>
      <ul>
        <NavItemTopicEntry
          v-for="subEntry in entry.entries"
          :key="subEntry.title"
          :entry="subEntry"
          :nav-item-id="navItemId"
        />
      </ul>
    </div>
    <NavItemTopicEntryLink v-else :entry="entry" :nav-item-id="navItemId"></NavItemTopicEntryLink>
  </li>
</template>

<style scoped>
li {
  list-style-type: none;
  margin-left: 26px;
  display: flex;
  align-items: center;

  .mm-nav-item-topic-entry {
    display: flex;
    flex-direction: column;

    ul {
      padding: 0;

      li {
        margin: 0;
      }
    }

    .mm-nav-item-topic-entry__indented-header {
      display: flex;
      flex-direction: row;
      align-items: center;
      margin-top: var(--dimension-5);

      .mm-nav-item-topic-entry__header-icon {
        margin-right: var(--dimension-4);
      }
    }
  }
}
</style>
