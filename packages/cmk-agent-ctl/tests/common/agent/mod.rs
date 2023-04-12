// Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#[cfg(unix)]
pub mod linux;
#[cfg(unix)]
pub use linux::is_elevation_required;

#[cfg(windows)]
pub mod win;
#[cfg(windows)]
pub use win::is_elevation_required;

#[cfg(windows)]
pub fn is_port_available(port: u16) -> bool {
    std::net::TcpListener::bind(("127.0.0.1", port)).is_ok()
}

#[cfg(unix)]
/// On Linux returns true always: this is initial behavior and subject to change in the future
/// with consequent merge both functions into one
pub fn is_port_available(_port: u16) -> bool {
    true
}
