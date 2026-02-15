from django.db import models
from django.utils import timezone


class MediaQuerySet(models.QuerySet):
    def initial(self, **kwargs):
        return self.filter(assessment_status=self.model.AssessmentStatus.INITIAL, **kwargs)

    def completed(self, **kwargs):
        return self.filter(assessment_status=self.model.AssessmentStatus.COMPLETED, **kwargs)

    def for_assessment(self, user_id: int, **kwargs):
        return (
            self.filter(
                assessment_status=self.model.AssessmentStatus.IN_PROGRESS,
                assessment_until_dt__gte=timezone.now(),
                **kwargs,
            )
            .exclude(assessments__user_id=user_id)
            .order_by('assessment_until_dt', 'name')
        )


class PollQuerySet(models.QuerySet):
    def initial(self, **kwargs):
        return self.filter(status=self.model.Status.INITIAL, **kwargs)
