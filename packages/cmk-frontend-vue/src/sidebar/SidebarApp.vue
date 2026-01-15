<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { type SidebarConfig } from 'cmk-shared-typing/typescript/sidebar'
import { provide, ref } from 'vue'

import usei18n from '@/lib/i18n'
import { KeyShortcutService } from '@/lib/keyShortcuts'

import CmkButton from '@/components/CmkButton.vue'
import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'
import CmkScrollContainer from '@/components/CmkScrollContainer.vue'

import { SidebarService } from '@/sidebar/lib/sidebar'

import AddSnapinSlideout from './components/AddSnapinSlideout.vue'
import SidebarSnapin from './components/snapin/SidebarSnapin.vue'
import { sidebarKey } from './provider/sidebar'

const { _t } = usei18n()
const props = defineProps<SidebarConfig>()

const sidebar = new SidebarService(
  props.snapins,
  props.update_interval,
  new KeyShortcutService(window)
)
provide(sidebarKey, sidebar)

const addSnapinSlideoutOpen = ref(false)

const draggedSnapin = ref<HTMLElement | null>(null)
const dropPlaceholder = ref<HTMLDivElement | null>(null)
const lastDragoverSnapinIndex = ref<number | null>(null)
const dragStartIndex = ref<number | null>(null)

function dragStart(e: DragEvent, index: number) {
  if (e.dataTransfer) {
    dragStartIndex.value = index
    e.dataTransfer.effectAllowed = 'move'
    draggedSnapin.value = (e.target as HTMLElement).closest('.sidebar-app__snapin') as HTMLElement

    dropPlaceholder.value = document.createElement('div')
    dropPlaceholder.value.classList.add('sidebar-app__drag-placeholder')
    dropPlaceholder.value.style.top = `${draggedSnapin.value.offsetTop}px`
  }
}

function dragOver(e: DragEvent, index: number) {
  let el = (e.target as HTMLElement).closest('.sidebar-app__snapin') as HTMLElement
  if (!el) {
    el = e.target as HTMLElement
  }

  if (draggedSnapin.value) {
    if (dropPlaceholder.value) {
      el.parentNode?.insertBefore(dropPlaceholder.value, draggedSnapin.value)
      dropPlaceholder.value.style.top = `${el.offsetTop}px`
    }
    if (draggedSnapin.value) {
      if (index !== dragStartIndex.value) {
        lastDragoverSnapinIndex.value = index
      }
    }
  }
}

function dragEnd(_e: DragEvent, index: number) {
  dropPlaceholder.value?.remove()
  dropPlaceholder.value = null

  if (typeof lastDragoverSnapinIndex.value === 'number') {
    void sidebar.moveSnapin(index, lastDragoverSnapinIndex.value)
  }

  lastDragoverSnapinIndex.value = dragStartIndex.value = draggedSnapin.value = null
}
</script>

<template>
  <div class="sidebar-app__wrapper">
    <CmkScrollContainer
      class="sidebar-app__snapin-container"
      max-height="calc(100vh - 64px)"
      type="outer"
    >
      <SidebarSnapin
        v-for="(snapin, index) in sidebar.snapinsRef.value"
        :key="snapin.name"
        ref="sidebar-snapin"
        class="sidebar-app__snapin"
        v-bind="snapin"
        :is-dragged="dragStartIndex === index"
        draggable="true"
        @dragover="dragOver($event, index)"
        @dragend="dragEnd($event, index)"
        @dragstart="dragStart($event, index)"
      />
      <div
        v-if="draggedSnapin"
        class="sidebar-app__drag-end"
        @dragover="dragOver($event, sidebar.snapinsRef.value.length)"
        @dragend="dragEnd($event, sidebar.snapinsRef.value.length)"
      ></div>
    </CmkScrollContainer>
    <div class="sidebar-app__add-snapin">
      <CmkButton @click="addSnapinSlideoutOpen = true">
        <CmkIcon name="plus" size="large" />
        <span>{{ _t('Add element') }}</span>
      </CmkButton>
    </div>
  </div>
  <AddSnapinSlideout v-model="addSnapinSlideoutOpen" />
</template>

<style scoped>
.sidebar-app__wrapper {
  width: 280px;
  height: 100vh;
  background: var(--default-nav-bg-color);
  display: flex;
  flex-direction: column;

  /* stylelint-disable-next-line selector-pseudo-class-no-unknown */
  :deep(.sidebar-app__drag-placeholder) {
    width: calc(100% - var(--dimension-4) * 2);
    height: 1px;
    margin: 0 var(--dimension-4);
    box-sizing: border-box;
    background: var(--ux-theme-4);
    border: 1px solid var(--color-white-80);
    position: absolute;
    border-radius: var(--border-radius);
  }

  .sidebar-app__snapin-container {
    flex-grow: 1;
    display: flex;
    flex-direction: column;
    position: relative;

    .sidebar-app__drag-end {
      height: 30px;
      position: relative;
      width: 100%;
    }
  }

  .sidebar-app__snapin:first-of-type {
    margin-top: var(--dimension-3);
  }

  .sidebar-app__add-snapin {
    display: flex;
    flex-direction: column;
    align-items: center;
    height: var(--dimension-8);
    padding: var(--dimension-5) 0;
    background: var(--default-nav-bg-color);
    width: 100%;
    box-sizing: border-box;

    button {
      display: flex;
      flex-direction: row;
      align-items: center;
      width: 90%;
      box-sizing: border-box;
      padding: var(--dimension-5);

      img {
        margin-right: var(--dimension-4);
      }
    }
  }
}
</style>
