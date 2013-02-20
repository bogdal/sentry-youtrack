# -*- encoding: utf-8 -*-
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
    summary = forms.CharField(
        label=_("Summary"),
        widget=forms.TextInput(attrs={'class': 'span9'})
    )
    description = forms.CharField(
        label=_("Description"),
        widget=forms.Textarea(attrs={"class": 'span9'})
    )
    type = forms.ChoiceField(
        label=_("Issue Type"),
        required=True
    )
    priority = forms.ChoiceField(
        label=_("Issue Priority"),
        required=True
    )

    def __init__(self, *args, **kwargs):
        super(YouTrackIssueForm, self).__init__(*args, **kwargs)

        initial = kwargs.get('initial')
        form_choices = initial.get('form_choices')

        self.fields["priority"].choices = form_choices['priority']
        self.fields["type"].choices = form_choices['type']

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
        label=_("Default Issue Type"),
        required=False
    )
    default_priority = forms.ChoiceField(
        label=_("Default Issue Priority"),
        required=False
    )

    def __init__(self, *args, **kwargs):
        super(YoutrackConfigurationForm, self).__init__(*args, **kwargs)

        initial = kwargs.get("initial")

        if initial:
            yt_client = self.get_youtrack_client(initial)

            projects = [(' ', u"- Choose project -")]
            for project in yt_client.get_projects():
                projects.append((project['shortname'], u"%s (%s)" % (project['name'], project['shortname'])))
            self.fields["project"].choices = projects

            choices = lambda x: (x, x)
            self.fields["default_priority"].choices = map(choices, yt_client.get_priorities())
            self.fields["default_type"].choices = map(choices, yt_client.get_issue_types())

            if not any(args) and not initial.get('project'):
                self.second_step_msg = u"%s %s" % (_("Your credentials are valid but plugin is NOT active yet."),
                                                   _("Please fill in remaining required fields."))
        else:
            del self.fields["project"]
            del self.fields["default_priority"]
            del self.fields["default_type"]

    def get_youtrack_client(self, data):
        yt_settings = {
            'url': data.get('url'),
            'username': data.get('username'),
            'password': data.get('password'),
        }
        return YouTrackClient(**yt_settings)

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

        try:
            self.get_youtrack_client(data)
        except (HTTPError, ConnectionError) as e:
            raise ValidationError(u"%s %s" % (_("Unable to connect to YouTrack."), e))

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
            "type": map(choices_func, yt_client.get_issue_types()),
        }

        return choices

    def get_initial_form_data(self, request, group, event, **kwargs):
        initial = {
            'project': self.get_option('project', group.project),
            'summary': self._get_group_title(request, group, event),
            'description': self._get_group_description(request, group, event),
            'priority': self.get_option('default_priority', group.project),
            'type': self.get_option('default_type', group.project),
            'form_choices': self.get_form_choices(group.project)
        }
        return initial

    def get_new_issue_title(self):
        return _("Create YouTrack Issue")

    def create_issue(self, request, group, form_data, **kwargs):
        yt_client = self.get_youtrack_client(group.project)
        issue = yt_client.create_issue(form_data)
        return issue['id']

    def get_issue_url(self, group, issue_id, **kwargs):
        url = self.get_option('url', group.project)
        return "%sissue/%s" % (url, issue_id)
