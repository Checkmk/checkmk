<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import CmkAccordion from '@/components/CmkAccordion/CmkAccordion.vue'
import CmkAccordionItem from '@/components/CmkAccordion/CmkAccordionItem.vue'
import CmkAccordionItemStateIndicator from '@/components/CmkAccordion/CmkAccordionItemStateIndicator.vue'
import CmkIcon from '@/components/CmkIcon'

const openedItems = ref(['item-1'])
</script>

<template>
  <CmkAccordion v-model="openedItems" :min-open="1" :max-open="1">
    <CmkAccordionItem value="item-1">
      <template #header>
        <div style="display: flex; align-items: center; gap: 8px">
          <CmkIcon name="users" />
          <span>Personal Information</span>
          <CmkAccordionItemStateIndicator value="item-1" />
        </div>
      </template>
      <template #content>
        <p>Manage your personal details, email address, and profile settings.</p>
      </template>
    </CmkAccordionItem>

    <CmkAccordionItem value="item-2">
      <template #header>
        <div style="display: flex; align-items: center; gap: 8px">
          <CmkIcon name="passwords" />
          <span>Security Settings</span>
        </div>
      </template>
      <template #content>
        <p>Update your password, enable 2FA, and manage security keys.</p>
      </template>
    </CmkAccordionItem>

    <CmkAccordionItem value="item-3">
      <template #header>
        <div style="display: flex; align-items: center; gap: 8px">
          <CmkIcon name="notifications" />
          <span>Notifications</span>
        </div>
      </template>
      <template #content>
        <p>Configure email digests and real-time alert preferences.</p>
      </template>
    </CmkAccordionItem>
  </CmkAccordion>
</template>
