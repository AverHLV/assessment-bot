from django.db import transaction

from asgiref.sync import sync_to_async
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field, StrictBool

from typing import Annotated

from api.assessment.models import Assessment, MediaCategory
from api.mcp.schemas.assessment import (
    DETAIL_FIELDS,
    PAGE_SIZE,
    REVIEW_MAX_LENGTH,
    SUMMARY_FIELDS,
    AssessmentDetail,
    AssessmentId,
    AssessmentPage,
    PageNumber,
    ReviewText,
    detail_from_row,
    summary_from_row,
)

ASSESSMENT_NOT_FOUND = 'No assessment found for the authenticated user.'


def authenticated_user_id() -> str:
    token = get_access_token()
    if token is None or not token.subject:
        raise ToolError('Authentication is required to access assessments.')
    return token.subject


async def list_assessments(
    page: PageNumber = 1,
    name: Annotated[
        str | None, Field(strict=True, description='Case-insensitive literal media title substring.')
    ] = None,
    category: Annotated[MediaCategory.Code | None, Field(description='Match this exact media category code.')] = None,
    partial: Annotated[
        StrictBool | None,
        Field(description='True: non-empty partial note; false: empty note; omitted: both.'),
    ] = None,
) -> AssessmentPage:
    """List only your own assessments, newest first, in fixed pages of 30.

    All supplied filters must match. Items contain assessment id, media id/title/category/meta mark,
    your mark (0–10 in half steps), partial note, and assessment creation time. Meta marks are 0–10 or null.
    No media URL, description, or review is returned. Use an item's top-level id as assessment_id in
    retrieve_assessment for full details. Empty or out-of-range pages return no items with correct totals.
    """

    queryset = Assessment.objects.filter(user_id=authenticated_user_id()).matching(
        name=name, category=category, partial=partial
    )
    total = await queryset.acount()
    offset = (page - 1) * PAGE_SIZE
    items = []
    if offset < total:
        rows = queryset.order_by('-create_dt', '-pk').values(*SUMMARY_FIELDS)[offset : offset + PAGE_SIZE]
        items = [summary_from_row(row) async for row in rows]

    return AssessmentPage(items=items, page=page, total=total, has_next=page * PAGE_SIZE < total)


async def retrieve_assessment(assessment_id: AssessmentId) -> AssessmentDetail:
    """Retrieve your own existing assessment by assessment_id (the list item's top-level id).

    Return your mark (0–10 in half steps), partial note, review, and creation time, with nested media
    id/title/category, meta mark (0–10 or null), URL, full description, assessment status and creation time.
    Empty notes/reviews are empty strings. Missing and other users' assessment IDs return the same error.
    """

    row = (
        await Assessment.objects.filter(user_id=authenticated_user_id(), pk=assessment_id)
        .values(*DETAIL_FIELDS)
        .afirst()
    )
    if row is None:
        raise ToolError(ASSESSMENT_NOT_FOUND)

    return detail_from_row(row)


def save_review(user_id: str, assessment_id: int, review: str) -> AssessmentDetail:
    with transaction.atomic():
        queryset = Assessment.objects.filter(user_id=user_id, pk=assessment_id)
        if not queryset.update(review=review):
            raise ToolError(ASSESSMENT_NOT_FOUND)

        return detail_from_row(queryset.values(*DETAIL_FIELDS).get())


async def update_review(assessment_id: AssessmentId, review: ReviewText) -> AssessmentDetail:
    """Replace or clear only the review of your existing assessment, identified by assessment_id.

    Trim surrounding whitespace; empty text clears the review. Never create an assessment or change its
    mark, partial note, or media. Return the same full detail object as retrieve_assessment, including
    your mark (0–10 in half steps) and media meta mark (0–10 or null). Repeating input is idempotent.
    Missing and other users' assessment IDs return the same error. No LLM reply is generated.
    Write the review in the user's first-person voice: use "I think" instead of "The user thinks".
    """

    return await sync_to_async(save_review, thread_sensitive=True)(authenticated_user_id(), assessment_id, review)


def register_assessment_tools(server: MCPServer) -> None:
    review_limit_description = f'Reviews are limited to {REVIEW_MAX_LENGTH} characters after trimming.'
    read_annotations = ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    )
    for tool in (list_assessments, retrieve_assessment):
        server.add_tool(
            tool,
            description=f'{tool.__doc__}\n{review_limit_description}',
            annotations=read_annotations,
            structured_output=True,
        )

    server.add_tool(
        update_review,
        description=f'{update_review.__doc__}\n{review_limit_description}',
        annotations=ToolAnnotations(
            read_only_hint=False,
            destructive_hint=True,
            idempotent_hint=True,
            open_world_hint=False,
        ),
        structured_output=True,
    )
