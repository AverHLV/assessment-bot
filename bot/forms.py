from django import forms
from django.core.exceptions import ValidationError
from django.forms.models import construct_instance

from api.assessment.models import Assessment, Media


class MediaForm(forms.ModelForm):
    class Meta:
        model = Media
        fields = 'name', 'url', 'description', 'category'

    def _post_clean(self):
        exclude = self._get_validation_exclusions()

        try:
            self.instance = construct_instance(self, self.instance, self._meta.fields, self._meta.exclude)
        except ValidationError as exc:
            self._update_errors(exc)

        # ModelChoiceField already loaded and validated category. Skip the redundant
        # ForeignKey existence query, but include category in model constraints below.
        try:
            self.instance.full_clean(exclude=exclude | {'category'}, validate_unique=False, validate_constraints=False)
        except ValidationError as exc:
            self._update_errors(exc)

        try:
            self.instance.validate_constraints(exclude=self._get_validation_exclusions())
        except ValidationError as exc:
            self._update_errors(exc)

        if self._validate_unique:
            self.validate_unique()


class AssessmentForm(forms.ModelForm):
    class Meta:
        model = Assessment
        fields = 'mark', 'partial', 'review'
