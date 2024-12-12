/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/* eslint-disable */
/**
 * This file is auto-generated via the cmk-shared-typing package.
 * Do not edit manually.
 */

export interface NotificationTypeDefs {
  notifications?: Notifications;
  notification_parameters_overview?: NotificationParametersOverview;
}
export interface Notifications {
  overview_title_i18n: string;
  fallback_warning?: FallbackWarning;
  notification_stats: NotificationStats;
  core_stats: CoreStats;
  rule_sections: RuleSection[];
  user_id: string;
}
export interface FallbackWarning {
  i18n: FallbackWarningI18N;
  setup_link: string;
  do_not_show_again_link: string;
}
export interface FallbackWarningI18N {
  title: string;
  message: string;
  setup_link_title: string;
  do_not_show_again_title: string;
}
export interface NotificationStats {
  num_sent_notifications: number;
  num_failed_notifications: number;
  sent_notification_link: string;
  failed_notification_link: string;
  i18n: NotificationStatsI18N;
}
export interface NotificationStatsI18N {
  sent_notifications: string;
  failed_notifications: string;
  sent_notifications_link_title: string;
  failed_notifications_link_title: string;
}
export interface CoreStats {
  sites: string[];
  i18n: CoreStatsI18N;
}
export interface CoreStatsI18N {
  title: string;
  sites_column_title: string;
  status_column_title: string;
  ok_msg: string;
  warning_msg: string;
  disabled_msg: string;
}
export interface RuleSection {
  i18n: string;
  topics: RuleTopic[];
}
export interface RuleTopic {
  i18n?: string;
  rules: Rule[];
}
export interface Rule {
  i18n: string;
  count: string;
  link: string;
}
export interface NotificationParametersOverview {
  parameters: RuleSection1[];
  i18n: {};
}
export interface RuleSection1 {
  i18n: string;
  topics: RuleTopic[];
}
