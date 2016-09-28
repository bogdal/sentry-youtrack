from hashlib import md5

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from requests.exceptions import ConnectionError, HTTPError, SSLError
from unidecode import unidecode

from .youtrack import YouTrackClient


VERIFY_SSL_CERTIFICATE = getattr(
    settings, 'YOUTRACK_VERIFY_SSL_CERTIFICATE', True)


class YouTrackProjectForm(forms.Form):

    PROJECT_FIELD_PREFIX = 'field_'

    FIELD_TYPE_MAPPING = {
        'float': forms.FloatField,
        'integer': forms.IntegerField,
        'date': forms.DateField,
        'string': forms.CharField,}

    project_field_names = {}

    def __init__(self, project_fields=None, *args, **kwargs):
        super(YouTrackProjectForm, self).__init__(*args, **kwargs)
        if project_fields is not None:
            self.add_project_fields(project_fields)

    def add_project_fields(self, project_fields):
        fields = []
        for field in project_fields:
            form_field = self._get_form_field(field)
            if form_field:
                form_field.widget.attrs = {
                    'class': 'project-field',
                    'data-field': field['name']}
                index = len(fields) + 1
                field_name = '%s%s' % (self.PROJECT_FIELD_PREFIX, index)
                self.fields[field_name] = form_field
                fields.append(form_field)
                self.project_field_names[field_name] = field['name']
        return fields

    def get_project_field_values(self):
        self.full_clean()
        values = {}
        for form_field_name, name in self.project_field_names.iteritems():
            values[name] = self.cleaned_data.get(form_field_name)
        return values

    def _get_initial(self, field_name):
        default_fields = self.initial.get('default_fields') or {}
        field_key = md5(unidecode(field_name)).hexdigest()
        return default_fields.get(field_key)

    def _get_form_field(self, project_field):
        field_type = project_field['type']
        field_values = project_field['values']
        form_field = self.FIELD_TYPE_MAPPING.get(field_type)
        kwargs = {
            'label': project_field['name'],
            'required': False,
            'initial': self._get_initial(project_field['name'])}
        if form_field:
            return form_field(**kwargs)
        if field_values:
            choices = zip(field_values, field_values)
            if "[*]" in field_type:
                if kwargs['initial']:
                    kwargs['initial'] = kwargs['initial'].split(',')
                return forms.MultipleChoiceField(choices=choices, **kwargs)
            kwargs['choices'] = [('', '-----')] + choices
            return forms.ChoiceField(**kwargs)


class NewIssueForm(YouTrackProjectForm):

    title = forms.CharField(
        label=_("Title"),
        widget=forms.TextInput(attrs={'class': 'span9'}))
    description = forms.CharField(
        label=_("Description"),
        widget=forms.Textarea(attrs={"class": 'span9'}))
    tags = forms.CharField(
        label=_("Tags"),
        help_text=_("Comma-separated list of tags"),
        widget=forms.TextInput(attrs={
            'class': 'span6', 'placeholder': "e.g. sentry"}),
        required=False)

    def clean_description(self):
        description = self.cleaned_data.get('description')
        description = description.replace('```', '{quote}')
        return description


class AssignIssueForm(forms.Form):

    issue = forms.CharField(
        label=_("YouTrack Issue"),
        widget=forms.TextInput(
            attrs={'class': 'span6', 'placeholder': _("Choose issue")}))


class DefaultFieldForm(forms.Form):

    field = forms.CharField(required=True, max_length=255)
    value = forms.CharField(required=False, max_length=255)

    def __init__(self, plugin, project, *args, **kwargs):
        super(DefaultFieldForm, self).__init__(*args, **kwargs)
        self.plugin = plugin
        self.project = project

    def save(self):
        data = self.cleaned_data
        default_fields = self.plugin.get_option(
            self.plugin.default_fields_key, self.project) or {}
        default_fields[md5(unidecode(data['field'])).hexdigest()] = data['value']
        self.plugin.set_option(
            self.plugin.default_fields_key, default_fields, self.project)


class YouTrackConfigurationForm(forms.Form):

    error_message = {
        'client': _("Unable to connect to YouTrack."),
        'invalid_ssl': _("SSL certificate  verification failed."),
        'invalid_password': _('Invalid username or password.'),
        'invalid_project': _('Invalid project: \'%s\''),
        'missing_fields': _('Missing required fields.'),
        'perms': _("User doesn't have Low-level Administration permissions."),
        'required': _("This field is required.")}

    url = forms.URLField(
        label=_("YouTrack Instance URL"),
        widget=forms.TextInput(
            attrs={'class': 'span9',
                   'placeholder': 'e.g. "https://yoursitename.myjetbrains.com/youtrack/"'}),
        required=True)
    username = forms.CharField(
        label=_("Username"),
        help_text=_("User should have admin rights."),
        widget=forms.TextInput(attrs={'class': 'span9'}),
        required=True)
    password = forms.CharField(
        label=_("Password"),
        help_text=_("Only enter a password if you want to change it"),
        widget=forms.PasswordInput(attrs={'class': 'span9'}),
        required=False)
    project = forms.ChoiceField(
        label=_("Linked Project"),
        required=True)
    default_tags = forms.CharField(
        label=_("Default tags"),
        help_text=_("Comma-separated list of tags"),
        widget=forms.TextInput(
            attrs={'class': 'span6', 'placeholder': "e.g. sentry"}),
        required=False)
    ignore_fields = forms.MultipleChoiceField(
        label=_("Ignore fields"),
        required=False,
        help_text=_("These fields will not appear on the form"))

    def __init__(self, *args, **kwargs):
        super(YouTrackConfigurationForm, self).__init__(*args, **kwargs)
        self.client_errors = {}

        initial = kwargs.get("initial")
        if initial:
            client = self.get_youtrack_client(initial)
            if not client:
                self.remove_fields()
            else:
                if initial.get('project'):
                    choices = self.get_ignore_field_choices(
                        client, initial.get('project'))
                    self.fields['ignore_fields'].choices = choices

                choices = self.get_project_field_choices(
                    client, initial.get('project'))
                self.fields["project"].choices = choices

                if not any(args) and not initial.get('project'):
                    self.second_step_msg = _(
                        "Your credentials are valid but plugin is NOT active "
                        "yet. Please fill in remaining required fields.")

            if self.client_errors and not args[0]:
                self.full_clean()
                for field, error in self.client_errors.items():
                    self._errors[field] = [error]
        else:
            self.remove_fields()

    def remove_fields(self):
        del self.fields["project"]
        del self.fields["default_tags"]
        del self.fields["ignore_fields"]

    def get_ignore_field_choices(self, client, project):
        try:
            fields = list(client.get_project_fields_list(project))
        except HTTPError:
            self.client_errors['project'] = self.error_message[
                'invalid_project'] % (project,)
        else:
            names = [field['name'] for field in fields]
            return zip(names, names)
        return []

    def get_project_field_choices(self, client, project):
        choices = [(' ', u"- Choose project -")]
        try:
            projects = list(client.get_projects())
        except HTTPError:
            self.client_errors['project'] = self.error_message[
                'invalid_project'] % (project, )
        else:
            for project in projects:
                display = "%s (%s)" % (project['name'], project['id'])
                choices.append((project['id'], display))
        return choices

    def get_youtrack_client(self, data, additional_params=None):
        yt_settings = {
            'url': data.get('url'),
            'username': data.get('username'),
            'password': data.get('password'),
            'verify_ssl_certificate': VERIFY_SSL_CERTIFICATE}
        if additional_params:
            yt_settings.update(additional_params)

        client = None
        try:
            client = YouTrackClient(**yt_settings)
        except (HTTPError, ConnectionError) as e:
            if e.response is not None and e.response.status_code == 403:
                self.client_errors['username'] = self.error_message[
                    'invalid_password']
            else:
                self.client_errors['url'] = self.error_message['client']
        except (SSLError, TypeError) as e:
            self.client_errors['url'] = self.error_message['invalid_ssl']
        if client:
            try:
                client.get_user(yt_settings.get('username'))
            except HTTPError as e:
                if e.response.status_code == 403:
                    self.client_errors['username'] = self.error_message['perms']
                    client = None
        return client

    def clean_password(self):
        password = (
            self.cleaned_data.get('password') or self.initial.get('password'))
        if not password:
            raise ValidationError(self.error_message['required'])
        return password

    def clean_project(self):
        project = self.cleaned_data.get('project').strip()
        if not project:
            raise ValidationError(self.error_message['required'])
        return project

    def clean(self):
        data = self.cleaned_data
        if not all(data.get(field)
                   for field in ('url', 'username', 'password')):
            raise ValidationError(self.error_message['missing_fields'])
        client = self.get_youtrack_client(data)
        if not client:
            for field, error in self.client_errors.items():
                self._errors[field] = [error]
                if field in data.keys():
                    del data[field]
        return data
