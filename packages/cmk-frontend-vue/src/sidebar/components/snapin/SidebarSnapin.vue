<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { type SidebarSnapin } from 'cmk-shared-typing/typescript/sidebar'
import { computed, ref } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'

import CmkCollapsible from '@/components/CmkCollapsible/CmkCollapsible.vue'
import CmkCollapsibleTitle from '@/components/CmkCollapsible/CmkCollapsibleTitle.vue'
import CmkMultitoneIcon from '@/components/CmkIcon/CmkMultitoneIcon.vue'
import type { CmkMultitoneIconColor, OneColorIcons } from '@/components/CmkIcon/types'
import CmkIconButton from '@/components/CmkIconButton.vue'
import CmkSkeleton from '@/components/CmkSkeleton.vue'

import { getInjectedSidebar } from '@/sidebar/provider/sidebar'

const props = defineProps<SidebarSnapin>()
const sidebar = getInjectedSidebar()
const snapinOpen = ref(props.open || false)
const snapinContent = ref<string | null>(null)

sidebar.onUpdateSnapinContent((contents) => {
  if (typeof contents[props.name] === 'string') {
    snapinContent.value = contents[props.name] as string
  }
})

const showMoreHover = ref<boolean>(false)

const showMoreColor = computed(() => {
  return (showMoreHover.value ? 'success' : 'font') as CmkMultitoneIconColor
})
const showMoreIcon = computed(() => {
  return (sidebar.showMoreIsActive(props.name) ? 'show-less' : 'show-more') as OneColorIcons
})
</script>

<template>
  <div class="sidebar-snapin__container">
    <CmkCollapsibleTitle
      :open="snapinOpen"
      :title="props.title as TranslatedString"
      @toggle-open="snapinOpen = !snapinOpen"
    />
    <button
      v-if="props.has_show_more_items"
      class="sidebar-snapin__show-more"
      @click="sidebar.toggleShowMoreLess(props.name)"
      @mouseenter="showMoreHover = true"
      @mouseleave="showMoreHover = false"
    >
      <CmkMultitoneIcon :name="showMoreIcon" :primary-color="showMoreColor" />
    </button>
    <CmkCollapsible :open="snapinOpen">
      <div class="sidebar-snapin__content-wrapper">
        <CmkSkeleton v-if="!snapinContent" class="sidebar-snapin__skel" />
        <template v-else>
          <!-- eslint-disable-next-line vue/no-v-html-->
          <div :class="{ more: sidebar.showMoreIsActive(props.name) }" v-html="snapinContent"></div>
          <!-- TODO: BKP replace click handler with snapin delete call: https://jira.lan.tribe29.com/browse/CMK-26152  -->
          <CmkIconButton class="sidebar-snapin__delete" name="delete" @click="() => {}" />
        </template>
      </div>
    </CmkCollapsible>
  </div>
</template>

<style scoped>
.sidebar-snapin__container {
  width: 100%;
  box-sizing: border-box;
  padding: var(--dimension-4) var(--dimension-7) 0 var(--dimension-7);
  position: relative;

  .sidebar-snapin__show-more {
    border: 0;
    background: none;
    padding: 0;
    margin: 0;
    position: absolute;
    top: var(--dimension-6);
    right: var(--dimension-7);
  }

  .sidebar-snapin__content-wrapper {
    border-bottom: 1px solid var(--default-border-color);
    padding: 0 0 var(--dimension-2) 0;
    margin-bottom: var(--dimension-3);
    display: flex;
    flex-direction: column;

    .sidebar-snapin__delete {
      opacity: 0;
      margin-top: var(--dimension-3);
      align-self: flex-end;
    }

    .sidebar-snapin__skel {
      height: 25px !important;
      border-radius: var(--border-radius);
    }
  }

  &:hover {
    .sidebar-snapin__delete {
      opacity: 1;
    }
  }
}
</style>
