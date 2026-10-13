<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAccordion from 'cmk-ui-library/components/CmkAccordion/CmkAccordion.vue'
import CmkAccordionItem from 'cmk-ui-library/components/CmkAccordion/CmkAccordionItem.vue'
import { ref } from 'vue'

const openedItems = ref(['item-1'])
</script>

<template>
  <CmkAccordion v-model="openedItems" :min-open="1" :max-open="1">
    <CmkAccordionItem value="item-1" icon="users">
      <template #header>Personal Information</template>
      <template #content>
        <p>Manage your personal details, email address, and profile settings.</p>
      </template>
    </CmkAccordionItem>

    <CmkAccordionItem value="item-2" icon="passwords">
      <template #header>Security Settings</template>
      <template #content>
        <p>Update your password, enable 2FA, and manage security keys.</p>
      </template>
    </CmkAccordionItem>

    <CmkAccordionItem value="item-3" icon="notifications">
      <template #header>Notifications</template>
      <template #content>
        <p>Configure email digests and real-time alert preferences.</p>
      </template>
    </CmkAccordionItem>
  </CmkAccordion>
</template>
