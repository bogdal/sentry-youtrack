import requests
import urllib
import json
from BeautifulSoup import BeautifulStoneSoup


class YouTrackClient(object):

    LOGIN_URL = '/rest/user/login'
    PROJECT_URL = '/rest/admin/project/<project_id>'
    PROJECTS_URL = '/rest/project/all'
    CREATE_URL = '/rest/issue'
    CUSTOM_FIELD_VALUES = '/rest/admin/customfield/<param_name>/<param_value>'

    def __init__(self, url, username, password):
        self.url = url.rstrip('/') if url else ''
        self._login(username, password)

    def _login(self, username, password):
        url = self.url + self.LOGIN_URL
        response = requests.post(url +
                                 "?login=" + urllib.quote_plus(username) +
                                 "&password=" + urllib.quote_plus(password))
        response.raise_for_status()
        self.cookies = response.cookies

    def _request(self, url):
        response = requests.get(url, cookies=self.cookies)
        response.raise_for_status()
        return BeautifulStoneSoup(response.text)

    def get_project_name(self, project_id):
        url = self.url + self.PROJECT_URL.replace('<project_id>', project_id)
        soap = self._request(url)
        return soap.project['name']

    def get_projects(self):
        url = self.url + self.PROJECTS_URL
        soap = self._request(url)
        return soap.projects

    def get_priorities(self):
        values = self.get_custom_field_values('bundle', 'Priorities')
        return [item.text for item in values.enumeration]

    def get_issue_types(self):
        values = self.get_custom_field_values('bundle', 'Types')
        return [item.text for item in values.enumeration]

    def get_custom_field_values(self, name, value):
        url = self.url + (self.CUSTOM_FIELD_VALUES
                          .replace("<param_name>", name)
                          .replace('<param_value>', value))

        response = requests.get(url, cookies=self.cookies)
        return BeautifulStoneSoup(response.text)

    def create_issue(self, data):
        url = self.url + self.CREATE_URL
        response = requests.post(url, cookies=self.cookies, data=data)
        response.raise_for_status()
        soap = BeautifulStoneSoup(response.text)
        return soap.issue
