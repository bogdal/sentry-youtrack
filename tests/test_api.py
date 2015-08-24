import os

import pytest
from vcr import VCR

from sentry_youtrack.youtrack import YouTrackClient


PROJECT_ID = 'myproject'

vcr = VCR(path_transformer=VCR.ensure_suffix('.yaml'),
          cassette_library_dir=os.path.join('tests', 'cassettes'))


@pytest.fixture
def youtrack_client():
    with vcr.use_cassette('youtrack_client.yaml'):
        client = YouTrackClient('https://youtrack.myjetbrains.com',
                                username='root', password='admin')
    return client


@vcr.use_cassette
def test_get_api_key(youtrack_client):
    assert youtrack_client.api_key == 'abcd1234'


@vcr.use_cassette
def test_get_project_name(youtrack_client):
    assert youtrack_client.get_project_name(PROJECT_ID) == 'My project'


@vcr.use_cassette
def test_get_projects(youtrack_client):
    expected_projects = [
        {'id': 'myproject', 'name': 'My project'},
        {'id': 'testproject', 'name': 'Test project'}]
    assert list(youtrack_client.get_projects()) == expected_projects


@vcr.use_cassette
def test_get_priorities(youtrack_client):
    priorities = [u'Show-stopper', u'Critical', u'Major', u'Normal', u'Minor']
    assert youtrack_client.get_priorities() == priorities


@vcr.use_cassette
def test_get_issue_types(youtrack_client):
    types = [u'Bug', u'Cosmetics', u'Exception', u'Feature', u'Task', 
             u'Usability Problem', u'Performance Problem', u'Epic', 
             u'Meta Issue', u'Auto-reported exception']
    assert youtrack_client.get_issue_types() == types


@vcr.use_cassette
def test_get_project_fields(youtrack_client):
    fields = [
        {'name': u'Priority',
         'values': [u'Show-stopper', u'Critical', u'Major', u'Normal', u'Minor'],
         'empty_text': u'No Priority',
         'type': u'enum[1]'},
        {'name': u'Type',
         'values': [u'Bug', u'Cosmetics', u'Exception', u'Feature', u'Task',
                    u'Usability Problem', u'Performance Problem', u'Epic',
                    u'Meta Issue', u'Auto-reported exception'], 
         'empty_text': u'No Type', 
         'type': u'enum[1]'}, 
        {'name': u'State',
         'values': [u'Submitted', u'Open', u'In Progress', u'To be discussed', 
                    u'Reopened', u"Can't Reproduce", u'Duplicate', u'Fixed', 
                    u"Won't fix", u'Incomplete', u'Obsolete',
                    u'Verified', u'New'],
         'empty_text': u'No State', 
         'type': u'state[1]'}, 
        {'name': u'Assignee',
         'values': [u'root'], 
         'empty_text': u'Unassigned', 
         'type': u'user[1]'}, 
        {'name': u'Subsystem',
         'values': [u'No subsystem'], 
         'empty_text': u'No Subsystem', 
         'type': u'ownedField[1]'}, 
        {'name': u'Fix versions',
         'values': [], 
         'empty_text': u'Unscheduled', 
         'type': u'version[*]'}, 
        {'name': u'Affected versions',
         'values': [], 
         'empty_text': u'Unknown', 
         'type': u'version[*]'}, 
        {'name': u'Fixed in build',
         'values': [], 
         'empty_text': u'Next Build', 
         'type': u'build[1]'}]
    assert list(youtrack_client.get_project_fields(PROJECT_ID)) == fields
