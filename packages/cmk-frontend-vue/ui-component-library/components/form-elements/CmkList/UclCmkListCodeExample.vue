<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import CmkList from '@/components/CmkList/CmkList.vue'

const itemsData = ref({
  names: ['Alice', 'Bob', 'Charlie'],
  roles: ['Admin', 'Editor', 'Viewer']
})

const handleAdd = () => {
  itemsData.value.names.push('New User')
  itemsData.value.roles.push('Viewer')
  return true
}

const handleDelete = (_index: number) => {
  return true
}
</script>

<template>
  <CmkList
    :items-props="itemsData"
    orientation="vertical"
    :try-delete="handleDelete"
    :add="{ show: true, tryAdd: handleAdd, label: 'Add User' }"
  >
    <template #item-props="{ names, roles }">
      <div>
        <strong>{{ names }}</strong> - <span>{{ roles }}</span>
      </div>
    </template>
  </CmkList>
</template>
