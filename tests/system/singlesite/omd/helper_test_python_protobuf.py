#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Tools are not aware of our generated test module
import test_pb2  # type: ignore[import-not-found]

address_book = test_pb2.AddressBook()

person = address_book.people.add()
person.id = 1234
person.name = "John Doe"
person.email = "jdoe@example.com"

serialized = address_book.SerializeToString()

address_book2 = test_pb2.AddressBook()
address_book2.ParseFromString(serialized)
print(len(address_book.people))
