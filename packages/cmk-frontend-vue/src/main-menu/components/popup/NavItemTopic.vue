<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { NavItemIdEnum, NavItemTopic } from 'cmk-shared-typing/typescript/main_menu'
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import CmkButton from '@/components/CmkButton.vue'
import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'

import { mapIcon } from '@/unified-search/providers/search-utils'
import type { SearchProviderKeys } from '@/unified-search/providers/search-utils.types'

import { getInjectedMainMenu } from '../../provider/main-menu'
import NavItemTopicEntry from './NavItemTopicEntry.vue'

const maxEntriesPerTopic = 10
const { _t } = usei18n()
const mainMenu = getInjectedMainMenu()

const props = defineProps<{
  topic: NavItemTopic
  navItemId: NavItemIdEnum
  isShowAll?: boolean | undefined
  flexGrow?: boolean | undefined
}>()

const icon = computed(() => {
  return mapIcon(props.topic.icon, props.navItemId as SearchProviderKeys)
})

function getEntries2Render() {
  if (props.isShowAll) {
    return props.topic.entries.slice(0)
  }

  return props.topic.entries
    .filter((e) => !e.show_more_mode || mainMenu.showMoreIsActive(props.navItemId))
    .slice(0)
}
</script>

<template>
  <div
    class="mm-nav-item-topic"
    :class="{
      'mm-nav-item-topic--grow': flexGrow || isShowAll,
      'mm-nav-item-topic--show-all': isShowAll
    }"
  >
    <div v-if="isShowAll" class="mm-nav-item-topic__show-all-back">
      <CmkButton @click="mainMenu.closeShowAllEntriesOfTopic(props.navItemId)">
        <CmkIcon name="back" class="mm-nav-item-topic__show-all-back-icon" />
        <span>{{ _t('Back') }}</span>
      </CmkButton>
    </div>
    <CmkHeading type="h3" class="mm-nav-item-topic__header">
      <CmkIcon
        :name="icon.name"
        :rotate="icon.rotate"
        size="large"
        class="mm-nav-item-topic__icon"
      ></CmkIcon>
      <span>{{ topic.title }}</span>
    </CmkHeading>
    <ul>
      <template v-for="entry in getEntries2Render()" :key="entry.title">
        <NavItemTopicEntry
          v-if="!entry.show_more_mode || mainMenu.showMoreIsActive(props.navItemId) || isShowAll"
          :entry="entry"
          :nav-item-id="navItemId"
        />
      </template>
      <li v-if="getEntries2Render().length > maxEntriesPerTopic && !props.isShowAll">
        <a
          href="javascript:void(0)"
          class="mm-nav-item-topic__show-all"
          @click="mainMenu.showAllEntriesOfTopic(props.navItemId, props.topic)"
          >{{ _t('Show all') }}</a
        >
      </li>
    </ul>
  </div>
</template>

<style scoped>
.mm-nav-item-topic {
  padding: var(--dimension-8);
  padding-bottom: 0;
  width: 250px;
  box-sizing: border-box;
  border-right: 1px solid var(--ux-theme-3);

  &.mm-nav-item-topic--grow {
    flex-grow: 1;
  }

  &.mm-nav-item-topic--show-all {
    width: 100%;
  }

  .mm-nav-item-topic__show-all-back {
    display: flex;
    flex-direction: row;
    align-items: center;
    margin-bottom: var(--dimension-8);

    .mm-nav-item-topic__show-all-back-icon {
      margin-right: var(--dimension-4);
    }
  }

  .mm-nav-item-topic__header {
    display: flex;
    flex-direction: row;
    align-items: center;

    .mm-nav-item-topic__icon {
      margin-right: var(--dimension-4);
    }
  }

  ul {
    padding: 0;
    margin: var(--dimension-3) 0 0;

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

        &.mm-nav-item-topic__show-all {
          font-weight: var(--font-weight-bold);
        }

        .mm-nav-item-topic__external-link {
          position: relative;
          opacity: 0.5;
          margin-left: var(--dimension-4);
        }

        .mm-nav-item-topic__toggle-chip {
          text-align: left;
        }

        .mm-nav-item-topic__toggle-button {
          flex-grow: 1;
          text-align: right;
        }
      }
    }
  }
}
</style>
