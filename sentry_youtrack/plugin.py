# -*- encoding: utf-8 -*-
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from sentry.plugins.bases.issue import IssuePlugin
from sentry.utils.cache import cache
from requests.exceptions import HTTPError, ConnectionError
from sentry_youtrack.youtrack import YouTrackClient
from sentry_youtrack import VERSION
from hashlib import md5


class YouTrackIssueForm(forms.Form):
    project = forms.CharField(widget=forms.HiddenInput())
    title = forms.CharField(
        label=_("Title"),
        widget=forms.TextInput(attrs={'class': 'span9'})
    )
    description = forms.CharField(
        label=_("Description"),
        widget=forms.Textarea(attrs={"class": 'span9'})
    )
    issue_type = forms.ChoiceField(
        label=_("Issue Type"),
        required=True
    )
    priority = forms.ChoiceField(
        label=_("Issue Priority"),
        required=True
    )
    tags = forms.CharField(
        label=_("Tags"),
        help_text=_("Comma-separated list of tags"),
        widget=forms.TextInput(attrs={'class': 'span6', 'placeholder': "e.g. sentry"}),
        required=False
    )

    def __init__(self, *args, **kwargs):
        super(YouTrackIssueForm, self).__init__(*args, **kwargs)

        initial = kwargs.get('initial')
        form_choices = initial.get('form_choices')

        self.fields["priority"].choices = form_choices['priority']
        self.fields["issue_type"].choices = form_choices['issue_type']

    def clean_description(self):
        description = self.cleaned_data.get('description')

        description = description.replace('```', '{quote}')

        return description


class YoutrackConfigurationForm(forms.Form):
    url = forms.URLField(
        label=_("YouTrack Instance URL"),
        widget=forms.TextInput(attrs={'class': 'span9', 'placeholder': 'e.g. "https://youtrack.myjetbrains.com/"'}),
        required=True
    )
    username = forms.CharField(
        label=_("Username"),
        help_text=_("User should have admin rights."),
        widget=forms.TextInput(attrs={'class': 'span9'}),
        required=True
    )
    password = forms.CharField(
        label=_("Password"),
        help_text=_("Only enter a password if you want to change it"),
        widget=forms.PasswordInput(attrs={'class': 'span9'}),
        required=False
    )
    project = forms.ChoiceField(
        label=_("Linked Project"),
        required=True
    )
    default_type = forms.ChoiceField(
        label=_("Issue Type"),
        required=False
    )
    default_priority = forms.ChoiceField(
        label=_("Issue Priority"),
        required=False
    )
    default_tags = forms.CharField(
        label=_("Tags"),
        help_text=_("Comma-separated list of tags"),
        widget=forms.TextInput(attrs={'class': 'span6', 'placeholder': "e.g. sentry"}),
        required=False
    )

    def __init__(self, *args, **kwargs):
        super(YoutrackConfigurationForm, self).__init__(*args, **kwargs)

        client = None
        initial = kwargs.get("initial")

        if initial:
            client = self.get_youtrack_client(initial)
            if not client and not args[0]:
                self.full_clean()
                self._errors['username'] = [self.youtrack_client_error]

        fieldsets = [
            Fieldset(
                None,
                'url',
                'username',
                'password',
                'project',
            )
        ]

        if initial and client:
            fieldsets.append(
                Fieldset(
                    _("Default values"),
                    'default_type',
                    'default_priority',
                    'default_tags')
            )
            projects = [(' ', u"- Choose project -")]
            for project in client.get_projects():
                projects.append((project['shortname'], u"%s (%s)" % (project['name'], project['shortname'])))
            self.fields["project"].choices = projects

            choices = lambda x: (x, x)
            self.fields["default_priority"].choices = map(choices, client.get_priorities())
            self.fields["default_type"].choices = map(choices, client.get_issue_types())

            if not any(args) and not initial.get('project'):
                self.second_step_msg = u"%s %s" % (_("Your credentials are valid but plugin is NOT active yet."),
                                                   _("Please fill in remaining required fields."))

        else:
            del self.fields["project"]
            del self.fields["default_priority"]
            del self.fields["default_type"]
            del self.fields["default_tags"]

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(*fieldsets)

    def get_youtrack_client(self, data):
        yt_settings = {
            'url': data.get('url'),
            'username': data.get('username'),
            'password': data.get('password'),
        }

        client = None

        try:
            client = YouTrackClient(**yt_settings)
        except (HTTPError, ConnectionError) as e:
            self.youtrack_client_error = u"%s %s" % (_("Unable to connect to YouTrack."), e)
        else:
            try:
                client.get_user(yt_settings.get('username'))
            except HTTPError as e:
                if e.response.status_code == 403:
                    self.youtrack_client_error = _("User doesn't have Low-level Administration permissions.")
                    client = None

        return client

    def clean_password(self):
        password = self.cleaned_data.get('password') or self.initial.get('password')

        if not password:
            raise ValidationError(_("This field is required."))

        return password

    def clean_project(self):
        project = self.cleaned_data.get('project').strip()

        if not project:
            raise ValidationError(_("This field is required."))

        return project

    def clean(self):
        data = self.cleaned_data

        if not all(data.get(field) for field in ('url', 'username', 'password')):
            raise ValidationError(_('Missing required fields'))

        client = self.get_youtrack_client(data)
        if not client:
            self._errors['username'] = self.error_class([self.youtrack_client_error])
            del data['username']

        return data


def cache_this(timeout=60):
    def decorator(func):
        def wrapper(*args, **kwargs):
            def get_cache_key(*args, **kwargs):
                params = list(args) + kwargs.values()
                return md5("".join(map(str, params))).hexdigest()
            key = get_cache_key(func.__name__, *args, **kwargs)
            result = cache.get(key)
            if not result:
                result = func(*args, **kwargs)
                cache.set(key, result, timeout)
            return result
        return wrapper
    return decorator


class YouTrackPlugin(IssuePlugin):
    author = u"Adam Bogdał"
    author_url = "https://github.com/bogdal/sentry-youtrack"
    version = VERSION
    slug = "youtrack"
    title = _("YouTrack")
    conf_title = title
    conf_key = slug
    new_issue_form = YouTrackIssueForm
    create_issue_template = "sentry_youtrack/create_issue_form.html"
    project_conf_form = YoutrackConfigurationForm
    project_conf_template = "sentry_youtrack/project_conf_form.html"

    resource_links = [
        (_("Bug Tracker"), "https://github.com/bogdal/sentry-youtrack/issues"),
        (_("Source"), "http://github.com/bogdal/sentry-youtrack"),
    ]
    
    def is_configured(self, request, project, **kwargs):
        return bool(self.get_option('project', project))

    def get_youtrack_client(self, project):
        settings = {
            'url': self.get_option('url', project),
            'username': self.get_option('username', project),
            'password': self.get_option('password', project),
        }
        return YouTrackClient(**settings)

    @cache_this(60)
    def get_form_choices(self, project):
        yt_client = self.get_youtrack_client(project)
        choices_func = lambda x: (x, x)

        choices = {
            "priority": map(choices_func, yt_client.get_priorities()),
            "issue_type": map(choices_func, yt_client.get_issue_types()),
        }

        return choices

    def get_initial_form_data(self, request, group, event, **kwargs):
        initial = {
            'project': self.get_option('project', group.project),
            'title': self._get_group_title(request, group, event),
            'description': self._get_group_description(request, group, event),
            'priority': self.get_option('default_priority', group.project),
            'issue_type': self.get_option('default_type', group.project),
            'tags': self.get_option('default_tags', group.project),
            'form_choices': self.get_form_choices(group.project)
        }
        return initial

    def get_new_issue_title(self):
        return _("Create YouTrack Issue")

    def create_issue(self, request, group, form_data, **kwargs):
        tags = filter(None, map(lambda x: x.strip(), form_data['tags'].split(',')))

        yt_client = self.get_youtrack_client(group.project)
        issue_data = {
            'project': form_data.get('project'),
            'summary': form_data.get('title'),
            'description': form_data.get('description'),
            'type': form_data.get('issue_type'),
            'priority': form_data.get('priority'),
        }
        issue_id = yt_client.create_issue(issue_data)['id']

        if tags:
            yt_client.add_tags(issue_id, tags)

        return issue_id

    def get_issue_url(self, group, issue_id, **kwargs):
        url = self.get_option('url', group.project)
        return "%sissue/%s" % (url, issue_id)
