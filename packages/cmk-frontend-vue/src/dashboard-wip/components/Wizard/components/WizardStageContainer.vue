<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<template>
  <div class="wizard-stage-container__steps-container">
    <div class="wizard-stage-container__steps-inner-container">
      <slot />
    </div>
  </div>
</template>

<style scoped>
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.wizard-stage-container__steps-container {
  flex: 2;
  height: 100vh;
  padding: var(--spacing-double);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.wizard-stage-container__steps-inner-container {
  height: 95vh;
  overflow-y: auto;
  position: relative;
}
</style>
