/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Component } from 'vue'

import AddHost from '@/welcome/components/steps/AddHost.vue'
import AdjustServices from '@/welcome/components/steps/AdjustServices.vue'
import AssignResponsibilities from '@/welcome/components/steps/AssignResponsibilities.vue'
import CreateDashboard from '@/welcome/components/steps/CreateDashboard.vue'
import EnableNotifications from '@/welcome/components/steps/EnableNotifications.vue'
import type { StepId } from '@/welcome/components/steps/utils'

export const stepComponents: { component: Component; stepNumber: number; stepId: StepId }[] = [
  { component: AddHost, stepNumber: 1, stepId: 'add_host' },
  { component: EnableNotifications, stepNumber: 2, stepId: 'enable_notifications' },
  { component: CreateDashboard, stepNumber: 3, stepId: 'create_dashboard' }
]

export const totalSteps = stepComponents.length

// Optional guides offered once onboarding is complete; they do not count towards progress.
// Their numbers continue after the steps, so a guide keeps its number in either tab.
export const furtherGuideComponents: {
  component: Component
  stepNumber: number
  stepId: StepId
}[] = [
  { component: AssignResponsibilities, stepNumber: 4, stepId: 'assign_responsibilities' },
  { component: AdjustServices, stepNumber: 5, stepId: 'adjust_services' }
]

// Only onboarding steps count, finished further guides must not.
export const countCompletedSteps = (finished: StepId[]): number =>
  stepComponents.filter(({ stepId }) => finished.includes(stepId)).length
