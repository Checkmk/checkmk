/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { StageInformation } from 'cmk-shared-typing/typescript/welcome'
import type { Component } from 'vue'

import AddHost from '@/welcome/components/steps/AddHost.vue'
import AdjustServices from '@/welcome/components/steps/AdjustServices.vue'
import AssignResponsibilities from '@/welcome/components/steps/AssignResponsibilities.vue'
import CreateDashboard from '@/welcome/components/steps/CreateDashboard.vue'
import EnableNotifications from '@/welcome/components/steps/EnableNotifications.vue'

import ActivateChanges from './ActivateChanges.vue'

export type StepId = StageInformation['finished'][number]

export const stepComponents: { component: Component; stepNumber: number; stepId: StepId }[] = [
  { component: AddHost, stepNumber: 1, stepId: 'add_host' },
  { component: ActivateChanges, stepNumber: 2, stepId: 'activate_changes' },
  {
    component: AdjustServices,
    stepNumber: 3,
    stepId: 'adjust_services'
  },
  { component: AssignResponsibilities, stepNumber: 4, stepId: 'assign_responsibilities' },
  { component: EnableNotifications, stepNumber: 5, stepId: 'enable_notifications' },
  { component: CreateDashboard, stepNumber: 6, stepId: 'create_dashboard' }
]

export const totalSteps = stepComponents.length
