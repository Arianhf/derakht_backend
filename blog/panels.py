from wagtail.admin.panels import FieldPanel
from django import forms
import jdatetime
from django.forms.widgets import DateInput


class JalaliDateInput(DateInput):
    def format_value(self, value):
        if value is None:
            return None
        if isinstance(value, str):
            return value
        return jdatetime.date.fromgregorian(date=value).strftime('%Y-%m-%d')


class JalaliDateField(forms.DateField):
    def __init__(self, **kwargs):
        kwargs['widget'] = JalaliDateInput(attrs={'type': 'date'})
        super().__init__(**kwargs)

    def to_python(self, value):
        if value in self.empty_values:
            return None
        try:
            jalali_date = jdatetime.datetime.strptime(value, '%Y-%m-%d').date()
            return jalali_date.togregorian()
        except (ValueError, TypeError):
            raise forms.ValidationError('Enter a valid date.')


class JalaliDatePanel(FieldPanel):
    def __init__(self, field_name, *args, **kwargs):
        super().__init__(field_name, *args, **kwargs)

    def get_form_class(self):
        Form = super().get_form_class()

        class UpdatedForm(Form):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.fields[self.panel.field_name] = JalaliDateField(
                    label=self.fields[self.panel.field_name].label,
                    required=self.fields[self.panel.field_name].required,
                    help_text=self.fields[self.panel.field_name].help_text
                )

        return UpdatedForm