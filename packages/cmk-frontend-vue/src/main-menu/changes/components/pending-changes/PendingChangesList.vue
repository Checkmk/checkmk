<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed, ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkCollapsible, { CmkCollapsibleTitle } from '@/components/CmkCollapsible'
import CmkIndent from '@/components/CmkIndent.vue'
import CmkScrollContainer from '@/components/CmkScrollContainer.vue'
import CmkZebra from '@/components/CmkZebra.vue'

import type { PendingChanges } from '../../ChangesInterfaces'
import PendingChangeItemText from './PendingChangeItemText.vue'

const { _t } = usei18n()

const props = defineProps<{
  pendingChanges: PendingChanges[]
  selectedSites: string[]
  numberOfForeignChanges: number
  userName: string
}>()

const pendingChangesCollapsible = ref<boolean>(true)

function filterPendingChanges(change: PendingChanges): boolean {
  return (
    (change.whichSites.includes('All sites') && props.selectedSites.length > 0) ||
    change.whichSites.some((site: string) => props.selectedSites.includes(site))
  )
}

const changesTitle = computed(() => {
  return _t('Changes: (%{n})', {
    n: props.pendingChanges.filter(filterPendingChanges).length
  })
})

const changesSideTitle = computed(() => {
  return _t('Foreign changes: (%{n})', { n: props.numberOfForeignChanges })
})
</script>

<template>
  <div
    v-if="selectedSites.length === 0 || pendingChanges.length > 0"
    class="pending-changes-container"
  >
    <CmkCollapsibleTitle
      :title="changesTitle"
      :side-title="changesSideTitle"
      class="collapsible-title"
      :open="pendingChangesCollapsible"
      @toggle-open="pendingChangesCollapsible = !pendingChangesCollapsible"
    />

    <CmkCollapsible :open="pendingChangesCollapsible" class="cmk-collapsible-pending-changes">
      <CmkIndent v-if="selectedSites.length === 0" class="cmk-indent-no-sites-selected-container">
        <div class="cmk-div-no-sites-selected">
          {{ _t("You haven't selected any sites") }}
        </div>
      </CmkIndent>
      <CmkScrollContainer
        v-if="selectedSites.length > 0"
        class="cmk-scroll-pending-changes-container"
        height="auto"
      >
        <div
          v-for="(change, idx) in pendingChanges.filter(filterPendingChanges)"
          :key="change.changeId"
          class="cmk-div-pending-changes-container"
        >
          <CmkIndent
            class="cmk-indent-pending-change-container"
            :class="{ 'red-text': change.user !== userName && change.user !== null }"
          >
            <CmkZebra :num="idx" class="pending-change__zebra">
              <PendingChangeItemText
                :text="change.changeText"
                class="cmk-span-pending-change-text"
              ></PendingChangeItemText>

              <div
                class="cmk-div-pending-change-details"
                :class="{ 'grey-text': change.user === userName || change.user === null }"
              >
                <div class="cmk-div-user-sites-timestamp">
                  <span>{{ change.user }}</span>
                  <span>|</span>
                  <span>{{ change.whichSites.join(', ') }}</span>
                </div>
                <span>{{ change.timestring }}</span>
              </div>
            </CmkZebra>
          </CmkIndent>
        </div>
      </CmkScrollContainer>
    </CmkCollapsible>
  </div>
</template>

<style scoped>
/* stylelint-disable checkmk/vue-bem-naming-convention */

.pending-changes-container {
  display: flex;
  flex-direction: column;
  width: 100%;
  margin-top: var(--dimension-8);
  margin-bottom: var(--dimension-6);
}

.collapsible-title {
  position: relative;
  height: auto;
  padding: 0 0 var(--dimension-4) var(--dimension-2);
  font-weight: bold;
  width: 100%;
  box-sizing: border-box;
}

.cmk-collapsible-pending-changes {
  width: 100%;
  height: calc(100% - 158px);
}

/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
:deep(.cmk-collapsible__content) {
  height: 100%;
}

.cmk-indent-no-sites-selected-container {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--dimension-3);
}

.cmk-div-no-sites-selected {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  color: var(--font-color-dimmed);
  margin-top: var(--dimension-6);
  margin-bottom: var(--dimension-6);
}

.cmk-scroll-pending-changes-container {
  width: 100%;
  display: flex;
  flex-direction: column;
}

.cmk-div-pending-changes-container {
  display: flex;
  width: 100%;
  padding: 0;
  flex-direction: column;
  align-items: flex-start;
}

.cmk-indent-pending-change-container {
  --margin-left: var(--dimension-4);

  display: flex;
  padding: 0 0 0 var(--dimension-4) !important;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--dimension-3);
  box-sizing: border-box;
  margin-top: 0;
  margin-bottom: 0;
  margin-left: var(--margin-left);
  width: calc(100% - var(--margin-left));
}

.pending-change__zebra {
  background-color: var(--default-bg-color);
  padding: var(--dimension-4);
  width: 100%;
  box-sizing: border-box;
}

.red-text {
  color: var(--color-danger);
}

.cmk-span-pending-change-text {
  display: flex;
  align-items: flex-start;
  flex-direction: column;
  align-self: stretch;
  color: var(--font-color);
}

.cmk-div-pending-change-details {
  display: flex;
  justify-content: space-between;
  align-items: center;
  align-self: stretch;
  color: var(--font-color-dimmed);
}

.grey-text {
  color: var(--font-color-dimmed);
}

.cmk-div-user-sites-timestamp {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
}
</style>
