/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { WelcomeCards } from 'cmk-shared-typing/typescript/welcome'

export const createMockCards = (): WelcomeCards => ({
  checkmk_ai: 'https://checkmk.com/ai',
  checkmk_docs: 'https://docs.checkmk.com',
  checkmk_forum: 'https://forum.checkmk.com',
  checkmk_best_practices: 'https://checkmk.com/best-practices',
  checkmk_trainings: 'https://checkmk.com/trainings',
  checkmk_webinars: 'https://checkmk.com/webinars',
  create_contactgroups: 'wato.py?mode=contact_groups',
  users: 'wato.py?mode=users',
  assign_host_to_contactgroups: 'wato.py?mode=edit_host',
  setup_backup: 'wato.py?mode=backup',
  scale_monitoring: 'wato.py?mode=distributed_monitoring',
  fine_tune_monitoring: 'wato.py?mode=globalvars',
  add_host: 'wato.py?mode=newhost',
  network_devices: 'wato.py?mode=newhost&host_type=snmp',
  aws_quick_setup: 'quick_setup.py?mode=aws',
  azure_quick_setup: 'quick_setup.py?mode=azure',
  gcp_quick_setup: 'quick_setup.py?mode=gcp',
  proxmox_quick_setup: 'wato.py?mode=new_special_agent_configuration',
  kubernetes_quick_setup: 'wato.py?mode=new_special_agent_configuration',
  activate_changes: 'wato.py?mode=changelog',
  setup_hosts: 'wato.py?mode=folder',
  main_dashboard: 'dashboard.py?name=main',
  problem_dashboard: 'dashboard.py?name=problems',
  unhandled_service_problems: 'view.py?view_name=svcproblems',
  time_periods: 'wato.py?mode=timeperiods',
  host_groups: 'wato.py?mode=host_groups',
  add_notification_rule: 'wato.py?mode=notification_rule',
  test_notifications: 'wato.py?mode=notifications',
  add_custom_dashboard: 'dashboard.py?mode=create',
  all_dashboards: 'dashboard.py',
  mark_step_completed: '/api/welcome/mark_step_completed',
  get_stage_information: '/api/welcome/get_stage_information',
  intro_users: 'https://docs.checkmk.com/2.5.0/en/intro_users.html?origin=checkmk',
  intro_notifications: 'https://docs.checkmk.com/2.5.0/en/intro_notifications.html?origin=checkmk',
  setup_folder_structure: 'https://docs.checkmk.com/2.5.0/en/host_structure.html?origin=checkmk',
  start_page: 'user_profile.py'
})
