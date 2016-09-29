import requests
import logging
from bs4 import BeautifulSoup

from sentry_youtrack import VERSION


logger = logging.getLogger(__name__)


class Session(requests.Session):

    def request(self, method, url, **kwargs):
        logger.debug('%s: %s' % (method, url))
        return super(Session, self).request(method, url, **kwargs)


class YouTrackError(Exception):
    pass


class YouTrackClient(object):

    LOGIN_URL = '/rest/user/login'
    PROJECT_URL = '/rest/admin/project/<project_id>'
    PROJECT_FIELDS = '/rest/admin/project/<project_id>/customfield'
    PROJECTS_URL = '/rest/project/all'
    CREATE_URL = '/rest/issue'
    ISSUES_URL = '/rest/issue/byproject/<project_id>'
    COMMAND_URL = '/rest/issue/<issue>/execute'
    CUSTOM_FIELD_VALUES = '/rest/admin/customfield/<param_name>/<param_value>'
    USER_URL = '/rest/admin/user/<user>'

    API_KEY_COOKIE_NAME = 'jetbrains.charisma.main.security.PRINCIPAL'

    def __init__(self, url, username=None, password=None, api_key=None,
                 verify_ssl_certificate=True):
        self.verify_ssl_certificate = verify_ssl_certificate
        self.url = url.rstrip('/') if url else ''
        if api_key is None:
            self.api_key = self._login(username, password)
        else:
            self.api_key = api_key
        self.cookies = {self.API_KEY_COOKIE_NAME: self.api_key}

    def _login(self, username, password):
        credentials = {
            'login': username,
            'password': password}
        url = self.url + self.LOGIN_URL
        response = self.request(url, data=credentials, method='post')
        if BeautifulSoup(response.text, 'xml').login is None:
            raise requests.HTTPError('Invalid YouTrack url')
        return response.cookies.get(self.API_KEY_COOKIE_NAME)

    def _get_bundle(self, response, bundle='enumeration'):
        soup = BeautifulSoup(response.text, 'xml')
        if soup.find('error'):
            raise YouTrackError(soup.find('error').string)

        bundle_method = '_get_%s_values' % bundle.lower()
        if hasattr(self, bundle_method):
            return getattr(self, bundle_method)(soup)

        return [item.text for item in getattr(soup, bundle)]

    def _get_userbundle_values(self, soup):
        def get_user_logins(xml):
            return [item['login'] for item in xml.findAll('user')]
        users = set(get_user_logins(soup.userBundle))
        for group in soup.userBundle.findAll('userGroup'):
            users.update(
                get_user_logins(self._get_users_from_group(group['name'])))
        return sorted(users)

    def _get_users_from_group(self, group):
        url = self.url + self.USER_URL.replace('/<user>', '')
        response = self.request(url, method='get', params={'group': group})
        return BeautifulSoup(response.text, 'xml').userRefs

    def _get_custom_field_values(self, name, value, bundle='enumeration'):
        url = self.url + (self.CUSTOM_FIELD_VALUES
                          .replace("<param_name>", name)
                          .replace('<param_value>', value))
        response = self.request(url, method='get')
        return self._get_bundle(response, bundle)

    def _get_custom_project_field_details(self, field):
        url = field['url']
        url = '%s%s' % (self.url, url[url.index('/rest/admin/'):])
        response = self.request(url, method='get')
        field_data = BeautifulSoup(response.text, 'xml')
        field_type = field_data.projectCustomField['type']
        type_prefix = field_type[:field_type.find('[')]

        type_name = "%sBundle" % type_prefix
        if type_prefix == 'enum':
            type_name = 'bundle'

        bundles = {
            'enum': 'enumeration',
            'state': 'stateBundle',
            'user': 'userBundle',
            'ownedField': 'ownedFieldBundle',
            'version': 'versions',
            'build': 'buildBundle'}

        values = None
        if field_data.param:
            kwargs = {
                'name': type_name,
                'value': field_data.param['value'],
                'bundle': bundles.get(type_prefix)}
            values = self._get_custom_field_values(**kwargs)

        field_details = {
            'name': field_data.projectCustomField['name'],
            'type': field_data.projectCustomField['type'],
            'empty_text': field_data.projectCustomField['emptyText'],
            'values': values}
        return field_details

    def request(self, url, data=None, params=None, method='get'):
        if method not in ['get', 'post']:
            raise AttributeError("Invalid method %s" % method)

        kwargs = {
            'url': url,
            'data': data,
            'params': params,
            'verify': self.verify_ssl_certificate,
            'headers': {
                'User-Agent': 'sentry-youtrack/%s' % VERSION}}

        if hasattr(self, 'cookies'):
            kwargs['cookies'] = self.cookies

        session = Session()
        if method == 'get':
            response = session.get(**kwargs)
        else:
            response = session.post(**kwargs)
        response.raise_for_status()
        return response

    def get_project_name(self, project_id):
        url = self.url + self.PROJECT_URL.replace('<project_id>', project_id)
        response = self.request(url, method='get')
        return BeautifulSoup(response.text, 'xml').project['name']

    def get_user(self, username):
        url = self.url + self.USER_URL.replace('<user>', username)
        response = self.request(url, method='get')
        return BeautifulSoup(response.text, 'xml').user

    def get_projects(self):
        url = self.url + self.PROJECTS_URL
        response = self.request(url, method='get')
        for project in BeautifulSoup(response.text, 'xml').projects:
            yield {'id': project['shortName'], 'name': project['name']}

    def get_priorities(self):
        return self._get_custom_field_values('bundle', 'Priorities')

    def get_issue_types(self):
        return self._get_custom_field_values('bundle', 'Types')

    def get_project_issues(self, project_id, query=None, offset=0, limit=15):
        url = self.url + self.ISSUES_URL.replace('<project_id>', project_id)
        params = {'max': limit, 'after': offset, 'filter': query}
        response = self.request(url, method='get', params=params)
        issues = [
            {'id': issue['id'],
             'state': issue.find("field", {'name': 'State'}).value.text,
             'summary': issue.find("field", {'name': 'summary'}).text}
            for issue in BeautifulSoup(response.text, 'xml').issues]
        return issues

    def create_issue(self, data):
        url = self.url + self.CREATE_URL
        response = self.request(url, data=data, method='post')
        return BeautifulSoup(response.text, 'xml').issue['id']

    def execute_command(self, issue, command):
        url = self.url + self.COMMAND_URL.replace('<issue>', issue)
        data = {'command': command}
        return self.request(url, data=data, method='post')

    def add_tags(self, issue, tags):
        for tag in tags:
            cmd = u'add tag %s' % tag
            self.execute_command(issue, cmd)

    def get_project_fields_list(self, project_id):
        url = self.url + self.PROJECT_FIELDS.replace('<project_id>', project_id)
        response = self.request(url, method='get')
        for field in BeautifulSoup(response.text, 'xml').projectCustomFieldRefs:
            yield {'name': field['name'], 'url': field['url']}

    def get_project_fields(self, project_id, ignore_fields=None):
        ignore_fields = ignore_fields or []
        for field in self.get_project_fields_list(project_id):
            if not field['name'] in ignore_fields:
                yield self._get_custom_project_field_details(field)
