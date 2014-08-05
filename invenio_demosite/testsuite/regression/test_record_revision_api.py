# -*- coding: utf-8 -*-

## This file is part of Invenio.
## Copyright (C) 2011 CERN.
##
## Invenio is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 2 of the
## License, or (at your option) any later version.
##
## Invenio is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with Invenio; if not, write to the Free Software Foundation, Inc.,
## 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""Records revision API regression tests"""

from time import sleep
from zlib import compress

from flask import url_for
from nose.tools import nottest

from invenio.base.wrappers import lazy_import
from invenio.testsuite import make_test_suite, \
                              run_test_suite, \
                              InvenioTestCase


Record = lazy_import('invenio.modules.records.api:Record')

get_record_revision_timestamps = lazy_import('invenio.legacy.bibedit.utils:'
                                             'get_record_revision_timestamps')
sorted_revision_timestamps = lazy_import('invenio.modules.records.utils:'
                                         'sorted_revision_timestamps')
bibupload = lazy_import('invenio.legacy.bibupload.engine:bibupload')


class RecordUpdater(object):

    """Callable singleton that updates a record with given MARCXML"""

    def __init__(self, recid=17, marc_update=None):
        """Set up recid and update MARCXML"""
        self.done = False
        self.recid = recid
        if marc_update is None:
            self.marc_update = """
            <record>
            <controlfield tag="001">{}</controlfield>
            <datafield tag="088" ind1=" " ind2=" "><subfield code="a">CERN-PPE-TEST</subfield></datafield>
            </record>
            """.format(recid)
        else:
            self.marc_update = marc_update

    def __call__(self, force=False):
        """Update record

        :param force: Updates record even if update already happened
        :returns:     Sorted record revisions
        :rtype:       List of revisions
        """
        if not self.done or force:
            record = Record.create(self.marc_update, master_format='marc')
            recstruct = record.legacy_create_recstruct()
            bibupload(recstruct, 'replace')
            self.done = True

        timestamps = get_record_revision_timestamps(self.recid)
        return sorted_revision_timestamps(timestamps)


update_record = RecordUpdater()


class TestInvenioRecordRevisionApi(InvenioTestCase):

    """Records revision API regression tests."""

    def setUp(self):
        """Update record"""
        self.revs = update_record()
        self.login('admin', '')

    def test_revision_api(self):
        """Test if correct record revision is returned"""
        old = Record.get_record(update_record.recid,
                                revision=self.revs[0])
        self.assertTrue('CERN-PPE-92-085' in str(old))
        self.assertTrue('CERN-PPE-TEST' not in str(old))
        new = Record.get_record(update_record.recid,
                                revision=self.revs[-1])
        self.assertTrue('CERN-PPE-TEST' in str(new))
        self.assertTrue('CERN-PPE-92-085' not in str(new))


class TestInvenioRecordRevisionView(InvenioTestCase):

    """Records revision view tests."""

    def setUp(self):
        """Update record"""
        self.revs = update_record()
        self.login('admin', '')

    def test_record_revision_information(self):
        """Test if revision URL parameter returns valid revision"""
        old = self.client.get(url_for('record.metadata', recid=17,
                                      revision=self.revs[0]),
            base_url=self.app.config['CFG_SITE_SECURE_URL'],
            follow_redirects=False)

        self.assert200(old)
        self.assertTrue('CERN-PPE-92-085' in old.data)
        self.assertTrue('CERN-PPE-TEST' not in old.data)

        # Try to rewrite in this manner:
        # old_url = url_for('record.metadata', recid=17,
        #    revision=self.revs[0])
        # test_web_page_content(old_url, expected_text='CERN-PPE-92-085',
        #    unexpected_text='CERN-PPE-TEST')

        new = self.client.get(url_for('record.metadata', recid=17,
                                      revision=self.revs[-1]),
            base_url=self.app.config['CFG_SITE_SECURE_URL'],
            follow_redirects=False)

        self.assert200(new)
        self.assertTrue('CERN-PPE-TEST' in new.data)
        self.assertTrue('CERN-PPE-92-085' not in new.data)

    def test_record_invalid_revision(self):
        """Test correct behavior when revision is invalid"""
        invalid = self.client.get(url_for('record.metadata', recid=17,
                                      revision=123123123123123123123),
            base_url=self.app.config['CFG_SITE_SECURE_URL'],
            follow_redirects=True)

        self.assertTrue('Redirect (302)' in invalid.data)

    def test_record_revision_nonexistent(self):
        """Test correct behavior when revision is valid yet doesn't exist"""
        non_existent = self.client.get(url_for('record.metadata', recid=17,
                                      revision=20140722083456),
            base_url=self.app.config['CFG_SITE_SECURE_URL'],
            follow_redirects=True)

        self.assertTrue('Redirect (302)' in non_existent.data)

    def test_record_revision_information_correct_export_links(self):
        """Test if export links keep the revision URL parameter"""
        old = self.client.get(url_for('record.metadata', recid=17,
                                      revision=self.revs[0]),
            base_url=self.app.config['CFG_SITE_SECURE_URL'],
            follow_redirects=False)
        formats = ['hx', 'hm', 'xm', 'xd', 'xe', 'xn', 'xw', 'xe']

        for of in formats:
            self.assertTrue('export/{}?ln=en'.format(of) not in old.data)
            self.assertTrue('export/{}?{}={}&ln=en'.format(of,
                self.app.config['CFG_RECORD_REVISION_URL_PARAMETER'],
                self.revs[0]) in old.data)

    @nottest
    def FIXME_test_record_correct_revision_export(self):
        """Test if export links provide correct revisions"""
        formats = ['hx', 'hm', 'xm', 'xd', 'xe', 'xn', 'xw', 'xe']

        for of in formats:
            old = self.client.get(url_for('record.metadata', recid=17,
                              of=of, revision=self.revs[0]),
                base_url=self.app.config['CFG_SITE_SECURE_URL'],
                follow_redirects=False)
            new = self.client.get(url_for('record.metadata', recid=17,
                              of=of, revision=self.revs[-1]),
                base_url=self.app.config['CFG_SITE_SECURE_URL'],
                follow_redirects=False)

            # self.assertTrue('CERN-PPE-92-085' in old.data)
            # self.assertTrue('CERN-PPE-TEST' not in old.data)

            # self.assertTrue('CERN-PPE-TEST' in new.data)
            # self.assertTrue('CERN-PPE-92-085' not in new.data)

    @nottest
    def FIXME_test_record_revision_files(self):
        """Test if appropriate file version for given revision are listed"""
        pass

    @nottest
    def FIXME_test_record_revision_comments(self):
        """Test if comments up to time of the given revision are shown"""
        pass


TEST_SUITE = make_test_suite(TestInvenioRecordRevisionView,
    TestInvenioRecordRevisionApi)

if __name__ == '__main__':
    run_test_suite(TEST_SUITE, warn_user=True)