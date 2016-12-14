# coding=utf-8
##
# Copyright (c) 2013-2016 Apple Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
##

"""
Directory tests
"""

from twisted.internet.defer import inlineCallbacks
from twistedcaldav.config import config
from twistedcaldav.test.util import StoreTestCase
from twext.who.directory import DirectoryRecord
from twext.who.idirectory import FieldName, RecordType
from txdav.who.directory import CalendarDirectoryRecordMixin, AutoScheduleMode
from twext.who.expression import (
    MatchType, MatchFlags, MatchExpression
)
from txdav.who.util import startswithFilter
from uuid import UUID


class TestDirectoryRecord(DirectoryRecord, CalendarDirectoryRecordMixin):
    pass


class DirectoryTestCase(StoreTestCase):

    @inlineCallbacks
    def test_expandedMembers(self):

        record = yield self.directory.recordWithUID(u"both_coasts")

        direct = yield record.members()
        self.assertEquals(
            set([u"left_coast", u"right_coast"]),
            set([r.uid for r in direct])
        )

        expanded = yield record.expandedMembers()
        self.assertEquals(
            set([u"Chris Lecroy", u"Cyrus Daboo", u"David Reid", u"Wilfredo Sanchez-Vega"]),
            set([r.displayName for r in expanded])
        )

    def test_canonicalCalendarUserAddress(self):

        record = TestDirectoryRecord(
            self.directory,
            {
                FieldName.uid: u"test",
                FieldName.shortNames: [u"name"],
                FieldName.recordType: RecordType.user,
            }
        )
        self.assertEquals(
            record.canonicalCalendarUserAddress(),
            u"urn:x-uid:test"
        )

        # Even with email address, canonical still remains urn:x-uid:

        record = TestDirectoryRecord(
            self.directory,
            {
                FieldName.uid: u"test",
                FieldName.shortNames: [u"name"],
                FieldName.emailAddresses: [u"test@example.com"],
                FieldName.recordType: RecordType.user,
            }
        )
        self.assertEquals(
            record.canonicalCalendarUserAddress(),
            u"urn:x-uid:test"
        )

    def test_calendarUserAddresses(self):
        """
        Verify the right CUAs are advertised, which no longer includes the
        /principals/ flavors (although those are still recognized by
        recordWithCalendarUserAddress( ) for backwards compatibility).
        """

        record = TestDirectoryRecord(
            self.directory,
            {
                FieldName.uid: u"test",
                FieldName.guid: UUID("E2F6C57F-BB15-4EF9-B0AC-47A7578386F1"),
                FieldName.shortNames: [u"name1", u"name2"],
                FieldName.emailAddresses: [u"test@example.com", u"another@example.com"],
                FieldName.recordType: RecordType.user,
            }
        )
        self.assertEquals(
            record.calendarUserAddresses,
            frozenset(
                [
                    u"urn:x-uid:test",
                    u"urn:uuid:E2F6C57F-BB15-4EF9-B0AC-47A7578386F1",
                    u"mailto:test@example.com",
                    u"mailto:another@example.com",
                ]
            )
        )

        record = TestDirectoryRecord(
            self.directory,
            {
                FieldName.uid: u"test",
                FieldName.shortNames: [u"name1", u"name2"],
                FieldName.recordType: RecordType.user,
            }
        )
        self.assertEquals(
            record.calendarUserAddresses,
            frozenset(
                [
                    u"urn:x-uid:test",
                ]
            )
        )

    @inlineCallbacks
    def test_recordsFromMatchExpression(self):
        expression = MatchExpression(
            FieldName.uid,
            u"6423F94A-6B76-4A3A-815B-D52CFD77935D",
            MatchType.equals,
            MatchFlags.none
        )
        records = yield self.directory.recordsFromExpression(expression)
        self.assertEquals(len(records), 1)

    @inlineCallbacks
    def test_recordsFromMatchExpressionNonUnicode(self):
        expression = MatchExpression(
            FieldName.guid,
            UUID("6423F94A-6B76-4A3A-815B-D52CFD77935D"),
            MatchType.equals,
            MatchFlags.caseInsensitive
        )
        records = yield self.directory.recordsFromExpression(expression)
        self.assertEquals(len(records), 1)

    @inlineCallbacks
    def test_recordWithCalendarUserAddress(self):
        """
        Make sure various CUA forms are recognized and hasCalendars is honored.
        Note: /principals/ CUAs are recognized but not advertised anymore; see
        record.calendarUserAddresses.
        """

        # hasCalendars
        record = yield self.directory.recordWithCalendarUserAddress(
            u"mailto:wsanchez@example.com"
        )
        self.assertNotEquals(record, None)
        self.assertEquals(record.uid, u"6423F94A-6B76-4A3A-815B-D52CFD77935D")

        record = yield self.directory.recordWithCalendarUserAddress(
            u"urn:x-uid:6423F94A-6B76-4A3A-815B-D52CFD77935D"
        )
        self.assertNotEquals(record, None)
        self.assertEquals(record.uid, u"6423F94A-6B76-4A3A-815B-D52CFD77935D")

        record = yield self.directory.recordWithCalendarUserAddress(
            u"urn:uuid:6423F94A-6B76-4A3A-815B-D52CFD77935D"
        )
        self.assertNotEquals(record, None)
        self.assertEquals(record.uid, u"6423F94A-6B76-4A3A-815B-D52CFD77935D")

        record = yield self.directory.recordWithCalendarUserAddress(
            u"/principals/__uids__/6423F94A-6B76-4A3A-815B-D52CFD77935D"
        )
        self.assertNotEquals(record, None)
        self.assertEquals(record.uid, u"6423F94A-6B76-4A3A-815B-D52CFD77935D")

        record = yield self.directory.recordWithCalendarUserAddress(
            u"/principals/users/wsanchez"
        )
        self.assertNotEquals(record, None)
        self.assertEquals(record.uid, u"6423F94A-6B76-4A3A-815B-D52CFD77935D")

        # no hasCalendars
        record = yield self.directory.recordWithCalendarUserAddress(
            u"mailto:nocalendar@example.com"
        )
        self.assertEquals(record, None)

    @inlineCallbacks
    def test_recordWithCalendarUserAddress_Bad(self):
        """
        Make sure various bad CUA forms are treated as missing records.
        """

        # Invalid UID format
        record = yield self.directory.recordWithCalendarUserAddress(
            u"urn:x-uid:***"
        )
        self.assertEquals(record, None)

        # Non-ascii UID format
        record = yield self.directory.recordWithCalendarUserAddress(
            u"urn:x-uid:åa"
        )
        self.assertEquals(record, None)

    @inlineCallbacks
    def test_recordWithCalendarUserAddress_no_fake_email(self):
        """
        Make sure that recordWithCalendarUserAddress handles fake emails for
        resources and locations.
        """

        record = yield self.directory.recordWithCalendarUserAddress(u"mailto:{}@do_not_reply".format("resource01".encode("hex")))
        self.assertTrue(record is None)
        record = yield self.directory.recordWithCalendarUserAddress(u"mailto:{}@do_not_reply".format("75EA36BE-F71B-40F9-81F9-CF59BF40CA8F".encode("hex")))
        self.assertTrue(record is None)
        record = yield self.directory.recordWithCalendarUserAddress(u"mailto:{}@do_not_reply".format("resource02".encode("hex")))
        self.assertTrue(record is None)

    @inlineCallbacks
    def test_calendarUserAddress_no_fake_email(self):
        """
        Make sure that recordWs have fake email addresses.
        """

        record = yield self.directory.recordWithUID(u"resource01")
        self.assertTrue(record is not None)
        self.assertTrue(len(getattr(record, "emailAddresses", ())) == 0)
        self.assertTrue(len([cuaddr for cuaddr in record.calendarUserAddresses if cuaddr.startswith("mailto:")]) == 0)

    @inlineCallbacks
    def test_recordsMatchingTokensNoFilter(self):
        """
        Records with names containing the token are returned
        """

        records = (yield self.directory.recordsMatchingTokens(
            [u"anche"]
        ))
        matchingShortNames = set()
        for r in records:
            for shortName in r.shortNames:
                matchingShortNames.add(shortName)
        self.assertTrue("dre" in matchingShortNames)
        self.assertTrue("wsanchez" in matchingShortNames)

    @inlineCallbacks
    def test_recordsMatchingTokensStartswithFilter(self):
        """
        Records with names starting with the token are returned, because of
        the filter installed.  Note that hyphens and spaces are used to split
        fullname into names.
        """
        self.directory.setFilter(startswithFilter)

        records = (yield self.directory.recordsMatchingTokens(
            [u"anche"]
        ))
        matchingShortNames = set()
        for r in records:
            for shortName in r.shortNames:
                matchingShortNames.add(shortName)
        self.assertTrue("dre" not in matchingShortNames)
        self.assertTrue("wsanchez" not in matchingShortNames)

        records = (yield self.directory.recordsMatchingTokens(
            [u"vega", u"wilf"]
        ))
        matchingShortNames = set()
        for r in records:
            for shortName in r.shortNames:
                matchingShortNames.add(shortName)
        self.assertTrue("dre" not in matchingShortNames)
        self.assertTrue("wsanchez" in matchingShortNames)

    @inlineCallbacks
    def test_getAutoScheduleMode(self):

        apollo = yield self.directory.recordWithUID(u"apollo")

        # both_coasts is the auto accept group, cdaboo is a member, and
        # sagen is not

        inGroup = yield self.directory.recordWithShortName(
            self.directory.recordType.user,
            u"cdaboo"
        )
        notInGroup = yield self.directory.recordWithShortName(
            self.directory.recordType.user,
            u"sagen"
        )

        expectations = (

            # the record's mode
            # effective mode when organizer is in the auto-accept-group
            # effective mode when organizer is not in the auto-accept-group

            (
                AutoScheduleMode.none,
                AutoScheduleMode.acceptIfFreeDeclineIfBusy,
                AutoScheduleMode.none,
            ),
            (
                AutoScheduleMode.accept,
                AutoScheduleMode.accept,
                AutoScheduleMode.accept,
            ),
            (
                AutoScheduleMode.decline,
                AutoScheduleMode.acceptIfFreeDeclineIfBusy,
                AutoScheduleMode.decline,
            ),
            (
                AutoScheduleMode.acceptIfFree,
                AutoScheduleMode.acceptIfFree,
                AutoScheduleMode.acceptIfFree,
            ),
            (
                AutoScheduleMode.declineIfBusy,
                AutoScheduleMode.acceptIfFreeDeclineIfBusy,
                AutoScheduleMode.declineIfBusy,
            ),
            (
                AutoScheduleMode.acceptIfFreeDeclineIfBusy,
                AutoScheduleMode.acceptIfFreeDeclineIfBusy,
                AutoScheduleMode.acceptIfFreeDeclineIfBusy,
            ),
        )

        for mode, inGroupMode, notInGroupMode in expectations:
            apollo.fields[self.directory.fieldName.autoScheduleMode] = mode

            # In auto accept group
            self.assertEquals(
                (
                    yield apollo.getAutoScheduleMode(
                        inGroup.canonicalCalendarUserAddress()
                    )
                ),
                inGroupMode
            )
            # Not in auto accept group
            self.assertEquals(
                (
                    yield apollo.getAutoScheduleMode(
                        notInGroup.canonicalCalendarUserAddress()
                    )
                ),
                notInGroupMode
            )

    @inlineCallbacks
    def test_setAutoScheduleMode(self):
        """
        Verify the record.setAutoScheduleMode( ) method
        """
        orion = yield self.directory.recordWithUID(u"orion")
        # Defaults to automatic
        self.assertEquals(orion.autoScheduleMode, AutoScheduleMode.acceptIfFreeDeclineIfBusy)
        # Change it to decline-if-busy
        yield orion.setAutoScheduleMode(AutoScheduleMode.declineIfBusy)
        # Refetch it
        orion = yield self.directory.recordWithUID(u"orion")
        # Verify it's changed
        self.assertEquals(orion.autoScheduleMode, AutoScheduleMode.declineIfBusy)


class DirectoryTestCaseFakeEmail(StoreTestCase):

    def configure(self):
        """
        Adjust the global configuration for this test.
        """
        super(StoreTestCase, self).configure()

        config.Scheduling.Options.FakeResourceLocationEmail = True

    @inlineCallbacks
    def test_recordWithCalendarUserAddress_fake_email(self):
        """
        Make sure that recordWithCalendarUserAddress handles fake emails for
        resources and locations.
        """

        record = yield self.directory.recordWithCalendarUserAddress(u"mailto:{}@do_not_reply".format("resource01".encode("hex")))
        self.assertTrue(record is not None)
        record = yield self.directory.recordWithCalendarUserAddress(u"mailto:{}@do_not_reply".format("75EA36BE-F71B-40F9-81F9-CF59BF40CA8F".encode("hex")))
        self.assertTrue(record is not None)
        record = yield self.directory.recordWithCalendarUserAddress(u"mailto:{}@do_not_reply".format("resource02".encode("hex")))
        self.assertTrue(record is None)

        # Make sure un-hex encoded variant works
        record = yield self.directory.recordWithCalendarUserAddress(u"mailto:{}@do_not_reply".format("75EA36BE-F71B-40F9-81F9-CF59BF40CA8F"))
        self.assertTrue(record is not None)

    @inlineCallbacks
    def test_calendarUserAddress_fake_email(self):
        """
        Make sure that records have fake email addresses.
        """

        record = yield self.directory.recordWithUID(u"resource01")
        self.assertTrue(record is not None)

        # Verify the fake email address is in fact unicode
        for address in record.emailAddresses:
            self.assertTrue(isinstance(address, unicode))

        self.assertIn(u"{}@do_not_reply".format("resource01".encode("hex")), record.emailAddresses)
        self.assertIn(u"mailto:{}@do_not_reply".format("resource01".encode("hex")), record.calendarUserAddresses)

    @inlineCallbacks
    def test_recordWithCalendarUserAddress_Bad(self):
        """
        Make sure various bad CUA forms are treated as missing records.
        """

        # Invalid fake email format - truncated base64
        record = yield self.directory.recordWithCalendarUserAddress(
            u"mailto:ZmF@do_not_reply"
        )
        self.assertEquals(record, None)

        # Invalid fake email format - invalid characters
        record = yield self.directory.recordWithCalendarUserAddress(
            u"mailto:****@do_not_reply"
        )
        self.assertEquals(record, None)

        # Non-ascii fake email format
        record = yield self.directory.recordWithCalendarUserAddress(
            u"mailto:åa@do_not_reply".encode("utf-8")
        )
        self.assertEquals(record, None)

        # Non-ascii fake email format
        record = yield self.directory.recordWithCalendarUserAddress(
            u"mailto:åa@do_not_reply"
        )
        self.assertEquals(record, None)
