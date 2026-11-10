// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <functional>
#include <string>
#include <unordered_set>

#include "StubObjects.h"
#include "gtest/gtest.h"
#include "livestatus/User.h"

TEST(UserTest, AuthUserMatchingContactName) {
    const StubContact contact{"King Kong"};
    const AuthUser user{contact, ServiceAuthorization::loose,
                        GroupAuthorization::loose,
                        [](const std::string &) { return nullptr; }};
    EXPECT_TRUE(user.is_authorized_for_contact_name("King Kong"));
}

TEST(UserTest, AuthUserNonMatchingContactName) {
    const StubContact contact{"King Kong"};
    const AuthUser user{contact, ServiceAuthorization::loose,
                        GroupAuthorization::loose,
                        [](const std::string &) { return nullptr; }};
    EXPECT_FALSE(user.is_authorized_for_contact_name("donald"));
}

TEST(UserTest, AuthUserEmptyContactName) {
    const StubContact contact{"King Kong"};
    const AuthUser user{contact, ServiceAuthorization::loose,
                        GroupAuthorization::loose,
                        [](const std::string &) { return nullptr; }};
    EXPECT_FALSE(user.is_authorized_for_contact_name(""));
}

TEST(UserTest, NoAuthUserAlwaysAuthorized) {
    const NoAuthUser user;
    EXPECT_TRUE(user.is_authorized_for_contact_name("anyone"));
    EXPECT_TRUE(user.is_authorized_for_contact_name(""));
}

TEST(UserTest, UnknownUserNeverAuthorized) {
    const UnknownUser user;
    EXPECT_FALSE(user.is_authorized_for_contact_name("anyone"));
    EXPECT_FALSE(user.is_authorized_for_contact_name(""));
}

// Tests for is_authorized_for_notification_object:
// Covers remote-site forwarded notifications where the host or service may not
// exist locally.

TEST(UserTest, NotificationObjectHostMissingAuthorizedByContactName) {
    // Host not found (null): fall back to contact name matching.
    const StubContact contact{"King Kong"};
    const AuthUser user{contact, ServiceAuthorization::loose,
                        GroupAuthorization::loose,
                        [](const std::string &) { return nullptr; }};
    EXPECT_TRUE(user.is_authorized_for_notification_object(
        nullptr, nullptr, /*is_service_notification=*/false, "King Kong"));
    EXPECT_FALSE(user.is_authorized_for_notification_object(
        nullptr, nullptr, /*is_service_notification=*/false, "donald"));
}

TEST(UserTest,
     NotificationObjectHostKnownServiceMissingAuthorizedByContactName) {
    // Host exists but service not found: fall back to contact name matching for
    // service notifications. This handles the case where a service existed in
    // the past or only exists on a remote site.
    const StubContact contact{"King Kong"};
    const StubHost host{{}};
    const AuthUser user{contact, ServiceAuthorization::loose,
                        GroupAuthorization::loose,
                        [](const std::string &) { return nullptr; }};
    EXPECT_TRUE(user.is_authorized_for_notification_object(
        &host, nullptr, /*is_service_notification=*/true, "King Kong"));
    EXPECT_FALSE(user.is_authorized_for_notification_object(
        &host, nullptr, /*is_service_notification=*/true, "donald"));
}

TEST(UserTest, NotificationObjectHostKnownNoServiceDescriptionUsesHostContact) {
    // Host exists, no service description (host notification): delegate to
    // host contact check, not contact name fallback.
    const StubContact contact{"King Kong"};
    const StubHost host_with_contact{{&contact}};
    const StubHost host_without_contact{{}};
    const AuthUser user{contact, ServiceAuthorization::loose,
                        GroupAuthorization::loose,
                        [](const std::string &) { return nullptr; }};
    // contact_name does NOT matter here — authorization is via hasContact()
    EXPECT_TRUE(user.is_authorized_for_notification_object(
        &host_with_contact, nullptr, /*is_service_notification=*/false,
        "donald"));
    EXPECT_FALSE(user.is_authorized_for_notification_object(
        &host_without_contact, nullptr, /*is_service_notification=*/false,
        "King Kong"));
}
