from django import forms

from api.assessment.models import Assessment, Media


class MediaForm(forms.ModelForm):
    class Meta:
        model = Media
        fields = 'name', 'url', 'description', 'category'


class AssessmentForm(forms.ModelForm):
    class Meta:
        model = Assessment
        fields = 'mark', 'partial'
