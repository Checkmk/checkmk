<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { SidebarSnapin } from 'cmk-shared-typing/typescript/sidebar'
import { ref } from 'vue'

import usei18n from '@/lib/i18n'
import { immediateWatch } from '@/lib/watch'

import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'
import CmkSlideInDialog from '@/components/CmkSlideInDialog.vue'

import type { TSidebarSnapin } from '@/sidebar/lib/type-defs'
import { getInjectedSidebar } from '@/sidebar/provider/sidebar'

import AddSidebarSnapin from './snapin/AddSidebarSnapin.vue'

const { _t } = usei18n()
const sidebar = getInjectedSidebar()
const slideInOpen = defineModel<boolean>({ required: true })
const availableSnapins = ref<TSidebarSnapin[] | null>(null)

function onClose() {
  slideInOpen.value = false
}

async function onAddSnapin(snapin: TSidebarSnapin) {
  await sidebar.addSnapin(snapin as SidebarSnapin)

  if (availableSnapins.value) {
    availableSnapins.value = availableSnapins.value?.filter((s) => s.name !== snapin.name)
  }
}

immediateWatch(
  () => ({ newSlideInOpen: slideInOpen.value }),
  async ({ newSlideInOpen }) => {
    if (newSlideInOpen) {
      availableSnapins.value = await sidebar.getAvailableSnapins()
      await sidebar.updateSnapinContent(availableSnapins.value.map((s) => s.name))
    }
  }
)
</script>

<template>
  <CmkSlideInDialog
    :header="{
      title: _t('Add sidebar element'),
      closeButton: true
    }"
    :open="slideInOpen"
    @close="onClose"
  >
    <a
      class="sidebar-add-snapin-slideout__custom-button"
      href="custom_snapins.py"
      target="main"
      @click="onClose"
    >
      <CmkIcon name="custom-snapin" />
      {{ _t('Custom sidebar elements') }}
    </a>
    <div class="sidebar-add-snapin-slideout__wrapper">
      <AddSidebarSnapin
        v-for="snapin in availableSnapins"
        :key="snapin.name"
        v-bind="snapin"
        @add-snapin="onAddSnapin"
      />
    </div>
  </CmkSlideInDialog>
</template>

<style scoped>
.sidebar-add-snapin-slideout__custom-button {
  display: inline-flex;
  height: var(--dimension-10);
  margin: 0;
  padding: 0 8px;
  align-items: center;
  justify-content: center;
  letter-spacing: unset;
  border-radius: var(--dimension-3);
  gap: var(--dimension-4);
  border: 1px solid var(--default-form-element-border-color);
  background: var(--default-nav-bg-color);
  text-decoration: none;
  font-weight: var(--font-weight-bold);

  &:hover {
    background: var(--color-midnight-grey-50);
  }
}

.sidebar-add-snapin-slideout__wrapper {
  display: flex;
  flex-flow: row wrap;
  width: 100%;
  position: relative;
  gap: var(--dimension-5);
  margin: var(--dimension-5) 0;
}
</style>
