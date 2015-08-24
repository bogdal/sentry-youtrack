from datetime import date

from django import forms
from sentry_youtrack.forms import YouTrackProjectForm


YOUTRACK_FIELDS = [
    {'type': 'float', 'name': 'f1', 'values': None},
    {'type': 'integer', 'name': 'f2', 'values': None},
    {'type': 'date', 'name': 'f3', 'values': None},
    {'type': 'string', 'name': 'f4', 'values': None},
    {'type': 'enum[1]', 'name': 'f5', 'values': ['t1', 't2', 't3']},
    {'type': 'state[1]', 'name': 'f6', 'values': ['t4', 't5', 't6']},
    {'type': 'version[*]', 'name': 'f7', 'values': ['t7', 't8', 't9']}]


def test_build_form_fields():
    form = YouTrackProjectForm(YOUTRACK_FIELDS)
    expected_field_types = [
        forms.FloatField,
        forms.IntegerField,
        forms.DateField,
        forms.CharField,
        forms.ChoiceField,
        forms.ChoiceField,
        forms.MultipleChoiceField]
    assert len(form.fields) == len(YOUTRACK_FIELDS)
    for index, form_field in enumerate(form.fields.values()):
        assert type(form_field) == expected_field_types[index]


def test_do_not_build_choice_field_without_value():
    fields = [
        # invalid fields - choice/multipleChoice fields without values
        {'type': 'version[*]', 'name': 'f8', 'values': None},
        {'type': 'version[1]', 'name': 'f9', 'values': ''},
        # valid field
        {'type': 'string', 'name': 'f10', 'values': None}]
    fields.extend(YOUTRACK_FIELDS)
    form = YouTrackProjectForm(fields)
    assert len(form.fields) == len(fields) - 2


def test_project_fields_values():
    data = {
        'field_1': 33.00,
        'field_2': 10,
        'field_3': '2013-01-01',
        'field_4': 'test',
        'field_5': 't2',
        'field_6': 't4',
        'field_7': ['t7', 't9']}
    expected_result = {
        'f1': 33.00,
        'f2': 10,
        'f3': date(2013, 1, 1),
        'f4': 'test',
        'f5': 't2',
        'f6': 't4',
        'f7': ['t7', 't9']}
    form = YouTrackProjectForm(YOUTRACK_FIELDS, data)
    assert form.get_project_field_values() == expected_result

