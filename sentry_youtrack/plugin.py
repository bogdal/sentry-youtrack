# -*- encoding: utf-8 -*-
import json

from django import forms
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse
from django.utils.translation import ugettext_lazy as _
from sentry.models import GroupMeta
from sentry.plugins.bases.issue import IssuePlugin

from . import VERSION
from .forms import (NewIssueForm, AssignIssueForm, DefaultFieldForm,
                    YouTrackConfigurationForm, YouTrackProjectForm,)
from .utils import cache_this
from .youtrack import YouTrackClient


class YouTrackPlugin(IssuePlugin):
    author = u"Adam Bogdał"
    author_url = "https://github.com/bogdal/sentry-youtrack"
    version = VERSION
    slug = "youtrack"
    title = _("YouTrack")
    conf_title = title
    conf_key = slug
    new_issue_form = NewIssueForm
    assign_issue_form = AssignIssueForm
    create_issue_template = "sentry_youtrack/create_issue_form.html"
    assign_issue_template = "sentry_youtrack/assign_issue_form.html"
    project_conf_form = YouTrackConfigurationForm
    project_conf_template = "sentry_youtrack/project_conf_form.html"
    project_fields_form = YouTrackProjectForm
    default_fields_key = 'default_fields'

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

    def get_project_fields(self, project):

        @cache_this(600)
        def cached_fields(ignore_fields):
            yt_client = self.get_youtrack_client(project)
            return yt_client.get_project_fields(
                self.get_option('project', project), ignore_fields)

        return cached_fields(self.get_option('ignore_fields', project))

    def get_initial_form_data(self, request, group, event, **kwargs):
        initial = {
            'title': self._get_group_title(request, group, event),
            'description': self._get_group_description(request, group, event),
            'tags': self.get_option('default_tags', group.project),
            'default_fields': self.get_option(self.default_fields_key,
                                              group.project)
        }
        return initial

    def get_new_issue_title(self):
        return _("Create YouTrack Issue")

    def get_existing_issue_title(self):
        return _("Assign existing YouTrack issue")

    def get_new_issue_form(self, request, group, event, **kwargs):
        if request.POST or request.GET.get('form'):
            project_fields = self.get_project_fields(group.project)
            return self.new_issue_form(project_fields,
                                       data=request.POST or None,
                                       initial=self.get_initial_form_data(
                                           request, group, event))
        return forms.Form()

    def create_issue(self, request, group, form_data, **kwargs):

        project_fields = self.get_project_fields(group.project)
        project_form = self.project_fields_form(project_fields, request.POST)
        project_field_values = project_form.get_project_field_values()

        tags = filter(None, map(lambda x: x.strip(),
                                form_data['tags'].split(',')))

        yt_client = self.get_youtrack_client(group.project)
        issue_data = {
            'project': self.get_option('project', group.project),
            'summary': form_data.get('title'),
            'description': form_data.get('description'),
        }

        issue_id = yt_client.create_issue(issue_data)['id']

        for field, value in project_field_values.iteritems():
            if value:
                value = [value] if type(value) != list else value
                cmd = map(lambda x: "%s %s" % (field, x), value)
                yt_client.execute_command(issue_id, " ".join(cmd))

        if tags:
            yt_client.add_tags(issue_id, tags)

        return issue_id

    def get_issue_url(self, group, issue_id, **kwargs):
        url = self.get_option('url', group.project)
        return "%sissue/%s" % (url, issue_id)

    def get_view_response(self, request, group):
        if request.is_ajax() and request.GET.get('action'):
            return self.view(request, group)
        return super(YouTrackPlugin, self).get_view_response(request, group)

    def actions(self, request, group, action_list, **kwargs):
        action_list = (super(YouTrackPlugin, self)
                       .actions(request, group, action_list, **kwargs))

        prefix = self.get_conf_key()
        if not GroupMeta.objects.get_value(group, '%s:tid' % prefix, None):
            url = self.get_url(group) + "?action=assign_issue"
            action_list.append((self.get_existing_issue_title(), url))
        return action_list

    def view(self, request, group, **kwargs):
        def get_action_view():
            action_view = "%s_view" % request.GET.get('action')
            if request.GET.get('action') and hasattr(self, action_view):
                return getattr(self, action_view)

        view = get_action_view() or super(YouTrackPlugin, self).view
        return view(request, group, **kwargs)

    def assign_issue_view(self, request, group):
        form = self.assign_issue_form(request.POST or None)

        if form.is_valid():
            issue_id = form.cleaned_data['issue']
            prefix = self.get_conf_key()
            GroupMeta.objects.set_value(group, '%s:tid' % prefix, issue_id)

            return self.redirect(group.get_absolute_url())

        context = {
            'form': form,
            'title': self.get_existing_issue_title(),
        }
        return self.render(self.assign_issue_template, context)

    def project_issues_view(self, request, group):
        project_issues = []
        query = request.POST.get('q')

        def get_int(value, default=0):
            try:
                return int(value)
            except ValueError:
                return default

        page = get_int(request.POST.get('page'), 1)
        page_limit = get_int(request.POST.get('page_limit'), 15)
        offset = (page-1) * page_limit

        yt_client = self.get_youtrack_client(group.project)
        project_id = self.get_option('project', group.project)
        issues = yt_client.get_project_issues(project_id,
                                              offset=offset,
                                              limit=page_limit + 1,
                                              query=query or None)

        for issue in issues:
            project_issues.append({
                'id': issue['id'],
                'state': issue.find("field", {'name': 'State'}).text,
                'summary': issue.find("field", {'name': 'summary'}).text})

        data = {
            'more': len(issues) > page_limit,
            'issues': project_issues[:page_limit]
        }
        return HttpResponse(json.dumps(data, cls=DjangoJSONEncoder))

    def save_field_as_default_view(self, request, group):
        form = DefaultFieldForm(self, group.project, request.POST or None)
        if form.is_valid():
            form.save()
        return HttpResponse()
