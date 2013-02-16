# -*- encoding: utf-8 -*-
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from sentry.plugins.bases.issue import IssuePlugin
from requests.exceptions import HTTPError, MissingSchema
from sentry_youtrack.youtrack import YouTrackClient
from sentry_youtrack import VERSION


class YouTrackIssueForm(forms.Form):
    project = forms.CharField(widget=forms.HiddenInput())
    summary = forms.CharField(
        label=_("Issue Summary"),
        widget=forms.TextInput(attrs={'class': 'span6'})
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={"class": 'span6'})
    )
    priority = forms.ChoiceField(
        label="Issue Priority",
        required=True
    )
    type = forms.ChoiceField(
        label="Issue Type",
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
    url = forms.CharField(
        label=_("YouTrack Instance URL"),
        widget=forms.TextInput(attrs={'class': 'span6', 'placeholder': 'e.g. "https://youtrack.myjetbrains.com/"'}),
        required=True
    )
    username = forms.CharField(
        label=_("Username"),
        widget=forms.TextInput(attrs={'class': 'span6'}),
        required=True
    )
    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(attrs={'class': 'span6'}),
        required=False
    )
    project = forms.ChoiceField(
        label=_("Linked Project"),
        required=True
    )
    default_type = forms.ChoiceField(
        label="Default Issue Type",
        required=False
    )
    default_priority = forms.ChoiceField(
        label="Default Issue Priority",
        required=False
    )

    def __init__(self, *args, **kwargs):
        super(YoutrackConfigurationForm, self).__init__(*args, **kwargs)

        initial = kwargs.get("initial")

        if initial:
            yt_client = self.get_youtrack_client(initial)

            projects = []
            for project in yt_client.get_projects():
                projects.append((project['shortname'], u"%s (%s)" % (project['name'], project['shortname'])))

            choices = lambda x: (x, x)

            self.fields["project"].choices = projects
            self.fields["default_priority"].choices = map(choices, yt_client.get_priorities())
            self.fields["default_type"].choices = map(choices, yt_client.get_issue_types())
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

    def clean(self):
        data = self.cleaned_data

        try:
            self.get_youtrack_client(data)
        except HTTPError as e:
            raise ValidationError("Unable to connect to YouTrack: %s" % e)
        except MissingSchema:
            raise ValidationError("Unable to connect to YouTrack")

        return data


class YouTrackPlugin(IssuePlugin):
    author = u"Adam Bogdał"
    author_url = "https://github.com/bogdal/sentry-youtrack"
    version = VERSION
    description = "Itegrate Youtrack issues by linking a repository to a project."
    slug = "youtrack"
    title = _("YouTrack")
    conf_title = title
    conf_key = slug
    new_issue_form = YouTrackIssueForm
    project_conf_form = YoutrackConfigurationForm

    resource_links = [
        ("Bug Tracker", "https://github.com/bogdal/sentry-youtrack/issues"),
        ("Source", "http://github.com/bogdal/sentry-youtrack"),
    ]
    
    def is_configured(self, request, project, **kwargs):
        if not self.get_option('project', project):
            return False
        return True

    def get_youtrack_client(self, project):
        settings = {
            'url': self.get_option('url', project),
            'username': self.get_option('username', project),
            'password': self.get_option('password', project),
        }
        return YouTrackClient(**settings)

    def get_form_choices(self, project):
        yt_client = self.get_youtrack_client(project)

        choices_func = lambda x: (x, x)
        choices = {}

        choices["priority"] = map(choices_func, yt_client.get_priorities())
        choices["type"] = map(choices_func, yt_client.get_issue_types())

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
        return "%s/issue/%s" % (url, issue_id)
