from django import forms

from api.assessment.models import Assessment


class AssessmentForm(forms.ModelForm):
    class Meta:
        model = Assessment
        fields = 'mark', 'partial'
