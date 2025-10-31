<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkButton from '@/components/CmkButton.vue'
import CmkCatalogPanel from '@/components/CmkCatalogPanel.vue'
import CmkSkeleton from '@/components/CmkSkeleton.vue'

const { _t } = usei18n()

const loadingContent = _t('Loading content...')
</script>

<template>
  <div class="loading-transition-catalog-skeleton">
    <div class="loading-transition-catalog-skeleton__page-menu-buttons">
      <CmkButton v-for="(_, nButton) in 4" :key="`button${nButton}`">
        <CmkSkeleton type="text" :width="['100px', '70px', '90px', '70px'][nButton]!" />
      </CmkButton>
    </div>
    <CmkCatalogPanel v-for="(_, nPanel) in 3" :key="`panel${nPanel}`" :title="loadingContent">
      <template #header>
        <CmkSkeleton type="text" :width="['150px', '250px', '150px'][nPanel]!"></CmkSkeleton>
      </template>
      <div class="loading-transition-catalog-skeleton__catalog-content">
        <CmkSkeleton
          v-for="n in [17, 4, 11][nPanel]!"
          :key="`panel${nPanel}.${n}`"
          type="text"
          :width="`${350 + Math.random() * 100}px`"
        />
      </div>
    </CmkCatalogPanel>
  </div>
</template>

<style scoped>
.loading-transition-catalog-skeleton {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-double);
}

.loading-transition-catalog-skeleton__page-menu-buttons {
  display: flex;
  flex-direction: row;
  gap: var(--spacing-half);
}

.loading-transition-catalog-skeleton__catalog-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing);
}
</style>
