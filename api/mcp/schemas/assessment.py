from pydantic import AwareDatetime, BaseModel, BeforeValidator, Field

from typing import Annotated

from api.assessment.models import Assessment, Media, MediaCategory

PAGE_SIZE = 30
REVIEW_MAX_LENGTH = Assessment._meta.get_field('review').max_length
SUMMARY_FIELDS = (
    'id',
    'media_id',
    'media__name',
    'media__category__code',
    'media__category__name',
    'media__meta_mark',
    'mark',
    'partial',
    'create_dt',
)
DETAIL_FIELDS = (
    *SUMMARY_FIELDS,
    'media__url',
    'media__description',
    'media__assessment_status',
    'media__create_dt',
    'review',
)


def trim_review(value: object) -> object:
    return value.strip() if isinstance(value, str) else value


PageNumber = Annotated[
    int, Field(strict=True, ge=1, description='1-based page number; each page has at most 30 items.')
]
AssessmentId = Annotated[
    int,
    Field(strict=True, description='Assessment identifier: the top-level id from a list item, not media.id.'),
]
ReviewText = Annotated[
    str,
    Field(
        strict=True,
        max_length=REVIEW_MAX_LENGTH,
        description=f'Replacement review; whitespace is trimmed before the {REVIEW_MAX_LENGTH}-character limit. '
        'Empty or whitespace-only text clears the review.',
    ),
    BeforeValidator(trim_review),
]


class CategoryDetails(BaseModel):
    code: MediaCategory.Code = Field(description='Stable media category code.')
    name: str = Field(description='Category display name.')


class MediaSummary(BaseModel):
    id: int = Field(description='Related media identifier; not an assessment lookup key.')
    name: str = Field(description='Media title.')
    category: CategoryDetails
    meta_mark: float | None = Field(description='External mark from 0 to 10 with one decimal precision, or null.')


class MediaDetail(MediaSummary):
    url: str = Field(description='URL describing the media.')
    description: str = Field(description='Full media description, including an empty string when absent.')
    assessment_status: Media.AssessmentStatus = Field(description='Current media assessment status code.')
    create_dt: AwareDatetime = Field(description='Media creation timestamp, ISO 8601 with timezone.')


class AssessmentSummary(BaseModel):
    id: int = Field(description='Assessment identifier; use as assessment_id in retrieve and review tools.')
    media: MediaSummary
    mark: float = Field(description="The authenticated user's mark from 0 to 10 in half steps.")
    partial: str = Field(description='Short note qualifying a partial assessment; empty when no note is recorded.')
    create_dt: AwareDatetime = Field(description='Assessment creation timestamp, ISO 8601 with timezone.')


class AssessmentDetail(AssessmentSummary):
    media: MediaDetail
    review: str = Field(description=f"The user's review, up to {REVIEW_MAX_LENGTH} characters; empty when absent.")


class AssessmentPage(BaseModel):
    items: list[AssessmentSummary] = Field(description='Matching assessments owned by the authenticated user.')
    page: int = Field(description='Requested 1-based page number.')
    page_size: int = Field(default=PAGE_SIZE, ge=PAGE_SIZE, le=PAGE_SIZE, description='Fixed number of items per page.')
    total: int = Field(description='Total number of own assessments matching all supplied filters.')
    has_next: bool = Field(description='Whether another page exists after this one.')


def summary_from_row(row: dict) -> AssessmentSummary:
    return AssessmentSummary(
        id=row['id'],
        media=MediaSummary(
            id=row['media_id'],
            name=row['media__name'],
            category=CategoryDetails(code=row['media__category__code'], name=row['media__category__name']),
            meta_mark=row['media__meta_mark'],
        ),
        mark=row['mark'],
        partial=row['partial'],
        create_dt=row['create_dt'],
    )


def detail_from_row(row: dict) -> AssessmentDetail:
    summary = summary_from_row(row)
    return AssessmentDetail(
        **summary.model_dump(exclude={'media'}),
        media=MediaDetail(
            **summary.media.model_dump(),
            url=row['media__url'],
            description=row['media__description'],
            assessment_status=row['media__assessment_status'],
            create_dt=row['media__create_dt'],
        ),
        review=row['review'],
    )
