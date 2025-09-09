<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkSkeleton from '@/components/CmkSkeleton.vue'

import ResultItemSkeleton from '../result/ResultItemSkeleton.vue'
import ResultList from '../result/ResultList.vue'

function getSkelNum(): number {
  const resultItemHeight = 54
  const offSetTop = 250
  const maxNum = 7
  const num = Math.floor((window.innerHeight - offSetTop) / resultItemHeight)
  return num > maxNum ? maxNum : num
}
</script>

<template>
  <div class="cmk-result-skeleton-wrapper">
    <CmkSkeleton type="h2" class="cmk-result-skeleton-header"></CmkSkeleton>
    <br />
    <ResultList>
      <ResultItemSkeleton v-for="i in getSkelNum()" :key="i"></ResultItemSkeleton>
    </ResultList>
  </div>
</template>

<style scoped>
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.cmk-result-skeleton-wrapper {
  margin: var(--spacing-double);
  display: flex;
  flex-direction: column;

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  .cmk-result-skeleton-header {
    width: 100px;
  }
}
</style>
