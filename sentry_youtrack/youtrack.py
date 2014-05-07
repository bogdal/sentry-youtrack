import requests
from BeautifulSoup import BeautifulStoneSoup


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

    def __init__(self, url, username=None, password=None, api_key=None, verify_ssl_certificate=True):
        self.verify_ssl_certificate = verify_ssl_certificate
        self.url = url.rstrip('/') if url else ''
        if api_key is None:
            self._login(username, password)
        else:
            self.api_key = api_key
        self.cookies = {self.API_KEY_COOKIE_NAME: self.api_key}

    def _login(self, username, password):
        credentials = {
            'login': username,
            'password': password
        }
        url = self.url + self.LOGIN_URL
        self._request(url, data=credentials, method='post')
        self.api_key = self.response.cookies.get(self.API_KEY_COOKIE_NAME)

    def _request(self, url, data=None, params=None, method='get'):
        if method not in ['get', 'post']:
            raise AttributeError("Invalid method %s" % method)

        kwargs = {
            'url': url,
            'data': data,
            'params': params,
            'verify': self.verify_ssl_certificate,
        }
        if hasattr(self, 'cookies'):
            kwargs['cookies'] = self.cookies

        if method == 'get':
            self.response = requests.get(**kwargs)
        elif method == 'post':
            self.response = requests.post(**kwargs)
        self.response.raise_for_status()
        return BeautifulStoneSoup(self.response.text)

    def _get_bundle(self, soap, bundle='enumeration'):
        if soap.find('error'):
            raise YouTrackError(soap.find('error').string)

        bundle_method = '_get_%s_values' % bundle
        if hasattr(self, bundle_method):
            return getattr(self, bundle_method)(soap)

        return [item.text for item in getattr(soap, bundle)]

    def _get_userbundle_values(self, soap):
        def get_user_logins(xml):
            return [item['login'] for item in xml.findAll('user')]
        users = set(get_user_logins(soap.userbundle))
        for group in soap.userbundle.findAll('usergroup'):
            users.update(get_user_logins(self.get_users_from_group(group['name'])))
        return sorted(users)

    def get_project_name(self, project_id):
        url = self.url + self.PROJECT_URL.replace('<project_id>', project_id)
        soap = self._request(url, method='get')
        return soap.project['name']

    def get_user(self, user):
        url = self.url + self.USER_URL.replace('<user>', user)
        soap = self._request(url, method='get')
        return soap.user

    def get_users_from_group(self, group):
        url = self.url + self.USER_URL.replace('/<user>', '')
        soap = self._request(url, method='get', params={'group': group})
        return soap.userrefs

    def get_projects(self):
        url = self.url + self.PROJECTS_URL
        soap = self._request(url, method='get')
        return soap.projects

    def get_priorities(self):
        values = self.get_custom_field_values('bundle', 'Priorities')
        return self._get_bundle(values)

    def get_issue_types(self):
        values = self.get_custom_field_values('bundle', 'Types')
        return self._get_bundle(values)

    def get_custom_field_values(self, name, value):
        url = self.url + (self.CUSTOM_FIELD_VALUES
                          .replace("<param_name>", name)
                          .replace('<param_value>', value))

        return self._request(url, method='get')

    def get_project_issues(self, project_id, query=None, offset=0, limit=15):
        url = self.url + self.ISSUES_URL.replace('<project_id>', project_id)
        params = {'max': limit, 'after': offset, 'filter': query}
        soap = self._request(url, method='get', params=params)
        return soap.issues

    def create_issue(self, data):
        url = self.url + self.CREATE_URL
        soap = self._request(url, data=data, method='post')
        return soap.issue

    def execute_command(self, issue, command):
        url = self.url + self.COMMAND_URL.replace('<issue>', issue)
        data = {'command': command}
        self._request(url, data=data, method='post')

    def add_tags(self, issue, tags):
        for tag in tags:
            cmd = u'add tag %s' % tag
            self.execute_command(issue, cmd)

    def get_project_fields_list(self, project_id):
        url = self.url + self.PROJECT_FIELDS.replace('<project_id>', project_id)
        soap = self._request(url, method='get')
        return soap.projectcustomfieldrefs

    def get_project_fields(self, project_id, ignore_fields=[]):
        fields = []
        for field in self.get_project_fields_list(project_id):
            if not field['name'] in ignore_fields:
                fields.append(self._get_custom_project_field_details(field))
        return fields

    def _get_custom_project_field_details(self, field):
        field_data = self._request(field['url'], method='get')
        field_type = field_data.projectcustomfield['type']
        type_prefix = field_type[:field_type.find('[')]

        type_name = "%sBundle" % type_prefix
        if type_prefix == 'enum':
            type_name = 'bundle'

        bundles = {
            'enum': 'enumeration',
            'state': 'statebundle',
            'user': 'userbundle',
            'ownedField': 'ownedfieldbundle',
            'version': 'versions',
            'build': 'buildbundle',
        }

        values = None
        if field_data.param:
            values = self.get_custom_field_values(type_name,
                                                  field_data.param['value'])
            values = self._get_bundle(values, bundles.get(type_prefix))

        field_details = {
            'name': field_data.projectcustomfield['name'],
            'type': field_data.projectcustomfield['type'],
            'empty_text': field_data.projectcustomfield['emptytext'],
            'values': values,
        }
        return field_details
