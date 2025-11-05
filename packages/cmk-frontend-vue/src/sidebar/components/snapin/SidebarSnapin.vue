<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed, nextTick, ref, useTemplateRef } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkAlertBox from '@/components/CmkAlertBox.vue'
import CmkCollapsible from '@/components/CmkCollapsible/CmkCollapsible.vue'
import CmkCollapsibleTitle from '@/components/CmkCollapsible/CmkCollapsibleTitle.vue'
import CmkMultitoneIcon from '@/components/CmkIcon/CmkMultitoneIcon.vue'
import type { CmkMultitoneIconColor, OneColorIcons } from '@/components/CmkIcon/types'
import CmkIconButton from '@/components/CmkIconButton.vue'
import CmkSkeleton from '@/components/CmkSkeleton.vue'

import type { TSidebarSnapin } from '@/sidebar/lib/type-defs'
import { getInjectedSidebar } from '@/sidebar/provider/sidebar'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
declare const cmk: any

const { _t } = usei18n()

interface SidebarSnapinProps extends TSidebarSnapin {
  isDragged?: boolean | undefined
}

const props = defineProps<SidebarSnapinProps>()
const sidebar = getInjectedSidebar()
const snapinOpen = ref(props.open || false)
const snapinContent = ref<string | null>(null)
const snapinContentElement = useTemplateRef('snapin-content')

sidebar.onUpdateSnapinContent((contents) => {
  if (typeof contents[props.name] === 'string') {
    snapinContent.value = contents[props.name] as string
    void nextTick(() => {
      cmk.utils.execute_javascript_by_object(snapinContentElement.value)
    })
  }
})

const showMoreHover = ref<boolean>(false)

const showMoreColor = computed(() => {
  return (showMoreHover.value ? 'success' : 'font') as CmkMultitoneIconColor
})
const showMoreIcon = computed(() => {
  return (sidebar.showMoreIsActive(props.name) ? 'show-less' : 'show-more') as OneColorIcons
})

async function onToggle() {
  snapinOpen.value = !snapinOpen.value
  await sidebar.persistSnapinToggleState(props.name, snapinOpen.value ? 'open' : 'closed')
}
</script>

<template>
  <div
    class="sidebar-snapin__container"
    :class="{ 'sidebar-snapin--drag-active': props.isDragged ?? false }"
  >
    <CmkCollapsibleTitle
      :open="snapinOpen"
      :title="props.title as TranslatedString"
      @toggle-open="onToggle"
    />
    <button
      v-if="props.has_show_more_items && snapinOpen"
      class="sidebar-snapin__show-more"
      @click="sidebar.toggleShowMoreLess(props.name)"
      @mouseenter="showMoreHover = true"
      @mouseleave="showMoreHover = false"
    >
      <CmkMultitoneIcon :name="showMoreIcon" :primary-color="showMoreColor" />
    </button>
    <CmkCollapsible :open="snapinOpen">
      <div class="sidebar-snapin__content-wrapper">
        <CmkSkeleton v-if="!snapinContent && snapinContent !== ''" class="sidebar-snapin__skel" />
        <!-- eslint-disable vue/no-v-html-->
        <template v-else>
          <CmkAlertBox v-if="snapinContent === ''" variant="info">
            {{ _t('No data recieved') }}
          </CmkAlertBox>
          <div
            v-else
            :id="`snapin_${name}`"
            ref="snapin-content"
            :class="{ more: sidebar.showMoreIsActive(props.name) }"
            v-html="snapinContent"
          ></div>
        </template>
        <CmkIconButton
          class="sidebar-snapin__delete"
          name="delete"
          @click="sidebar.removeSnapin(props.name)"
        />
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

  &.sidebar-snapin--drag-active {
    opacity: 0.2;
  }

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
