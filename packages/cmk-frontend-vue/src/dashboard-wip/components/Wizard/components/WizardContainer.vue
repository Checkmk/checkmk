<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<template>
  <div class="create-edit-dashlet__external-container">
    <div class="create-edit-dashlet__main-container">
      <slot />
    </div>
  </div>
</template>

<style scoped>
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.create-edit-dashlet__external-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.create-edit-dashlet__main-container {
  display: flex;
  width: 100%;
  flex: 1;
  height: 100%;
  column-gap: var(--spacing);
}
</style>
