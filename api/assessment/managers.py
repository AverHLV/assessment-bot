from django.db import models


class MediaCategoryQuerySet(models.QuerySet):
    def movie(self):
        return self.get(code=self.model.Code.MOVIE)

    def game(self):
        return self.get(code=self.model.Code.GAME)


class MediaQuerySet(models.QuerySet):
    def initial(self, **kwargs):
        return self.filter(assessment_status=self.model.AssessmentStatus.INITIAL, **kwargs)

    def completed(self, **kwargs):
        return self.filter(assessment_status=self.model.AssessmentStatus.COMPLETED, **kwargs)

    def for_assessment(self, user_id: int, **kwargs):
        return (
            self.filter(
                assessment_status=self.model.AssessmentStatus.IN_PROGRESS,
                **kwargs,
            )
            .exclude(assessments__user_id=user_id)
            .order_by('name')
        )


class AssessmentQuerySet(models.QuerySet):
    def matching(self, *, name: str | None = None, category: str | None = None, partial: bool | None = None):
        queryset = self
        if name:
            queryset = queryset.filter(media__name__icontains=name)
        if category is not None:
            queryset = queryset.filter(media__category__code=category)
        if partial is True:
            queryset = queryset.exclude(partial='')
        elif partial is False:
            queryset = queryset.filter(partial='')

        return queryset


class PollQuerySet(models.QuerySet):
    def initial(self, **kwargs):
        return self.filter(status=self.model.Status.INITIAL, **kwargs)
