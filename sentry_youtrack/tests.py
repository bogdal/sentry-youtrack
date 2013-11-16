from datetime import date
from unittest import TestCase

from django import forms

from .forms import YouTrackProjectForm


class YouTrackProjectFormTest(TestCase):

    def setUp(self):

        self.youtrack_fields = [
            {'type': 'float', 'name': 'f1', 'values': None},
            {'type': 'integer', 'name': 'f2', 'values': None},
            {'type': 'date', 'name': 'f3', 'values': None},
            {'type': 'string', 'name': 'f4', 'values': None},
            {'type': 'enum[1]', 'name': 'f5', 'values': ['t1', 't2', 't3']},
            {'type': 'state[1]', 'name': 'f6', 'values': ['t4', 't5', 't6']},
            {'type': 'version[*]', 'name': 'f7', 'values': ['t7', 't8', 't9']},
        ]

    def test_build_form_fields(self):

        form = YouTrackProjectForm(self.youtrack_fields)
        self.assertEqual(len(form.fields), len(self.youtrack_fields))

        expected_field_types = [
            forms.FloatField,
            forms.IntegerField,
            forms.DateField,
            forms.CharField,
            forms.ChoiceField,
            forms.ChoiceField,
            forms.MultipleChoiceField
        ]

        for index, form_field in enumerate(form.fields.values()):
            self.assertEqual(type(form_field), expected_field_types[index])

    def test_do_not_build_choice_field_without_value(self):

        fields = [
            # choice/multipleChoice fields without values
            {'type': 'version[*]', 'name': 'f8', 'values': None},
            {'type': 'version[1]', 'name': 'f9', 'values': ''},
            # ok
            {'type': 'string', 'name': 'f10', 'values': None},
        ]
        fields.extend(self.youtrack_fields)

        form = YouTrackProjectForm(fields)
        self.assertEqual(len(form.fields), len(fields) - 2)

    def test_project_fields_values(self):

        data = {
            'field_1': 33.00,
            'field_2': 10,
            'field_3': '2013-01-01',
            'field_4': 'test',
            'field_5': 't2',
            'field_6': 't4',
            'field_7': ['t7', 't9']
        }

        expected_result = {
            self.youtrack_fields[0]['name']: 33.00,
            self.youtrack_fields[1]['name']: 10,
            self.youtrack_fields[2]['name']: date(2013, 1, 1),
            self.youtrack_fields[3]['name']: 'test',
            self.youtrack_fields[4]['name']: 't2',
            self.youtrack_fields[5]['name']: 't4',
            self.youtrack_fields[6]['name']: ['t7', 't9']
        }

        form = YouTrackProjectForm(self.youtrack_fields, data)
        self.assertEqual(form.get_project_field_values(), expected_result)
