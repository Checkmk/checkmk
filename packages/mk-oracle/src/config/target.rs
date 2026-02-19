// Copyright (C) 2026 Checkmk GmbH
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// SPDX-License-Identifier: Apache-2.0

use crate::types::{DescriptorSid, InstanceAlias, InstanceName, ServiceName, ServiceType, Sid};

#[derive(PartialEq, Debug, Clone)]
pub struct Descriptor {
    service_name: ServiceName,
    service_type: Option<ServiceType>,
    instance_name: Option<InstanceName>,
    sid: Option<DescriptorSid>,
}

#[derive(PartialEq, Debug, Clone)]
pub enum TargetId {
    Descriptor(Descriptor),
    Sid(Sid),
    Alias(InstanceAlias),
    NoId,
}

impl TargetId {
    pub fn service_name(&self) -> Option<&ServiceName> {
        match self {
            TargetId::Descriptor(descriptor) => Some(&descriptor.service_name),
            _ => None,
        }
    }

    pub fn instance_name(&self) -> Option<&InstanceName> {
        match self {
            TargetId::Descriptor(descriptor) => descriptor.instance_name.as_ref(),
            _ => None,
        }
    }

    pub fn descriptor_sid(&self) -> Option<&DescriptorSid> {
        match self {
            TargetId::Descriptor(descriptor) => descriptor.sid.as_ref(),
            _ => None,
        }
    }

    pub fn service_type(&self) -> Option<&ServiceType> {
        match self {
            TargetId::Descriptor(descriptor) => descriptor.service_type.as_ref(),
            _ => None,
        }
    }

    pub fn standalone_sid(&self) -> Option<&Sid> {
        match self {
            TargetId::Sid(sid) => Some(sid),
            _ => None,
        }
    }

    pub fn raw_sid(&self) -> Option<&str> {
        match self {
            TargetId::Sid(sid) => Some(<&str>::from(sid)),
            TargetId::Descriptor(d) => {
                let s = &d.sid;
                s.as_ref().map(<&str>::from)
            }
            _ => None,
        }
    }

    pub fn alias(&self) -> Option<&InstanceAlias> {
        match self {
            TargetId::Alias(alias) => Some(alias),
            _ => None,
        }
    }

    pub fn display_name(&self) -> String {
        match &self {
            TargetId::Alias(alias) => alias.to_string(),
            TargetId::Sid(sid) => sid.to_string(),
            TargetId::Descriptor(descriptor) => descriptor
                .instance_name
                .as_ref()
                .map_or_else(|| descriptor.service_name.to_string(), ToString::to_string),
            TargetId::NoId => "undefined".to_string(),
        }
    }
}

pub struct TargetIdBuilder {
    service_name: Option<ServiceName>,
    sid: Option<String>,
    alias: Option<InstanceAlias>,
    instance_name: Option<InstanceName>,
    service_type: Option<ServiceType>,
}

impl TargetIdBuilder {
    pub fn new() -> Self {
        Self {
            service_name: None,
            sid: None,
            alias: None,
            instance_name: None,
            service_type: None,
        }
    }
    pub fn service_name(mut self, service_name: Option<&ServiceName>) -> Self {
        self.service_name = service_name.cloned();
        self
    }

    pub fn sid(mut self, sid: Option<&str>) -> Self {
        self.sid = sid.map(|s| s.to_string());
        self
    }

    pub fn alias(mut self, alias: Option<&InstanceAlias>) -> Self {
        self.alias = alias.cloned();
        self
    }

    pub fn instance_name(mut self, instance_name: Option<&InstanceName>) -> Self {
        self.instance_name = instance_name.cloned();
        self
    }
    pub fn service_type(mut self, service_type: Option<&ServiceType>) -> Self {
        self.service_type = service_type.cloned();
        self
    }

    pub fn build(self) -> TargetId {
        if let Some(alias) = self.alias {
            TargetId::Alias(alias)
        } else if let Some(service_name) = self.service_name {
            TargetId::Descriptor(Descriptor {
                service_name,
                service_type: self.service_type,
                instance_name: self.instance_name,
                sid: self.sid.map(DescriptorSid::from),
            })
        } else if let Some(sid) = self.sid {
            TargetId::Sid(Sid::from(sid))
        } else {
            TargetId::NoId
        }
    }
}

impl Default for TargetIdBuilder {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default() {
        let target_id = TargetIdBuilder::default().build();
        assert!(matches!(target_id, TargetId::NoId));
    }

    fn create_descriptor(
        service_name: &str,
        instance_name: Option<&str>,
        sid: Option<&str>,
    ) -> Descriptor {
        Descriptor {
            service_name: ServiceName::from(service_name),
            service_type: None,
            instance_name: instance_name.map(InstanceName::from),
            sid: sid.map(DescriptorSid::from),
        }
    }

    #[test]
    fn test_service_name_from_descriptor() {
        let descriptor = create_descriptor("my_service", None, None);
        let target_id = TargetId::Descriptor(descriptor);

        assert_eq!(
            target_id.service_name().map(|s| s.to_string()),
            Some("my_service".to_string())
        );
    }

    #[test]
    fn test_service_name_from_sid() {
        let target_id = TargetId::Sid(Sid::from("ORCL"));
        assert!(target_id.service_name().is_none());
    }

    #[test]
    fn test_service_name_from_alias() {
        let target_id = TargetId::Alias(InstanceAlias::from("my_alias".to_string()));
        assert!(target_id.service_name().is_none());
    }

    #[test]
    fn test_all_from_noid() {
        assert!(TargetId::NoId.service_name().is_none());
        assert!(TargetId::NoId.instance_name().is_none());
        assert!(TargetId::NoId.alias().is_none());
    }

    #[test]
    fn test_instance_name_from_descriptor_with_instance() {
        let descriptor = create_descriptor("service", Some("instance"), None);
        let target_id = TargetId::Descriptor(descriptor);

        assert_eq!(
            target_id.instance_name().map(|s| s.to_string()),
            Some("INSTANCE".to_string())
        );
    }

    #[test]
    fn test_instance_name_from_descriptor_without_instance() {
        let descriptor = create_descriptor("service", None, None);
        let target_id = TargetId::Descriptor(descriptor);

        assert!(target_id.instance_name().is_none());
    }

    #[test]
    fn test_instance_name_from_non_descriptor() {
        assert!(TargetId::Sid(Sid::from("ORCL")).instance_name().is_none());
        assert!(TargetId::Alias(InstanceAlias::from("alias".to_string()))
            .instance_name()
            .is_none());
    }

    #[test]
    fn test_sid_from_descriptor_with_sid() {
        let descriptor = create_descriptor("service", None, Some("ORCL"));
        let target_id = TargetId::Descriptor(descriptor);

        assert_eq!(
            target_id.descriptor_sid().map(|s| s.to_string()),
            Some("ORCL".to_string())
        );
        assert!(target_id.standalone_sid().is_none());
    }

    #[test]
    fn test_sid_from_descriptor_without_sid() {
        let descriptor = create_descriptor("service", None, None);
        let target_id = TargetId::Descriptor(descriptor);

        assert!(target_id.descriptor_sid().is_none());
        assert!(target_id.standalone_sid().is_none());
    }

    #[test]
    fn test_sid_from_sid() {
        let target_id = TargetId::Sid(Sid::from("ORCL"));
        assert_eq!(
            target_id.standalone_sid().map(|s| s.to_string()),
            Some("ORCL".to_string())
        );
        assert!(target_id.descriptor_sid().is_none());
    }

    #[test]
    fn test_sid_from_alias() {
        let target_id = TargetId::Alias(InstanceAlias::from("alias".to_string()));
        assert!(target_id.standalone_sid().is_none());
        assert!(target_id.descriptor_sid().is_none());
    }

    #[test]
    fn test_alias_from_alias() {
        let target_id = TargetId::Alias(InstanceAlias::from("my_alias".to_string()));
        assert_eq!(
            target_id.alias().map(|s| s.to_string()),
            Some("my_alias".to_string())
        );
    }

    #[test]
    fn test_alias_from_non_alias() {
        let descriptor = create_descriptor("service", None, None);
        assert!(TargetId::Descriptor(descriptor).alias().is_none());
        assert!(TargetId::Sid(Sid::from("ORCL")).alias().is_none());
        assert!(TargetId::NoId.alias().is_none());
    }
}
