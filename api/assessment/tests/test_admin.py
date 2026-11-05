from django.conf import settings
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory, TestCase, override_settings
from django.urls import resolve, reverse

import factory

from decimal import Decimal

from api.assessment.admin import start_assessment
from api.assessment.models import Assessment, Media
from api.assessment.tests.factories import AssessmentFactory, MediaFactory
from api.user.tests.factories import UserFactory


@override_settings(
    STORAGES={
        **settings.STORAGES,
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    }
)
class AssessmentAdminTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(is_staff=True, is_superuser=True)
        cls.media = MediaFactory.create_batch(
            size=3,
            creator=cls.user,
            assessment_status=factory.Iterator(Media.AssessmentStatus.values),
            meta_mark=Decimal('7.5'),
            description='Description',
            url='https://example.com/story',
        )
        cls.assessment = AssessmentFactory(user=cls.user, media=cls.media[0], review='Admin review')

    def get_request(self, view_name, *args):
        request = RequestFactory().get(reverse(view_name, args=args))
        request.user = self.user
        request.resolver_match = resolve(request.path)
        return request

    def test__media_admin__start_changes_only_status_for_selected_rows(self):
        selected_ids = [media.pk for media in self.media[:2]]
        before = {row['id']: row for row in Media.objects.values()}

        with self.assertNumQueries(1):
            start_assessment(admin.site._registry[Media], None, Media.objects.filter(pk__in=selected_ids))

        after = {row['id']: row for row in Media.objects.values()}
        for pk, row in before.items():
            if pk in selected_ids:
                row['assessment_status'] = Media.AssessmentStatus.IN_PROGRESS
            self.assertEqual(after[pk], row)
        self.assertEqual(start_assessment.short_description, 'Start assessment for the selected media')

    def test__media_admin__start_empty_selection(self):
        before = list(Media.objects.values())

        with self.assertNumQueries(1):
            start_assessment(admin.site._registry[Media], None, Media.objects.filter(pk=-1))

        self.assertEqual(list(Media.objects.values()), before)

    def test__media_admin__list_has_no_deadline_or_deferred_columns(self):
        model_admin = admin.site._registry[Media]
        request = self.get_request('admin:assessment_media_changelist')
        changelist = model_admin.get_changelist_instance(request)

        with self.assertNumQueries(1):
            rows = [
                (
                    row.pk,
                    row.name,
                    row.create_dt,
                    row.update_dt,
                    row.assessment_status,
                    row.meta_mark,
                    row.category.name,
                    model_admin.display_creator(row),
                )
                for row in changelist.result_list
            ]

        self.assertEqual(len(rows), 3)
        self.assertTrue(all(row[5] == Decimal('7.5') for row in rows))
        self.assertNotIn('assessment_until_dt', model_admin.get_list_display(request))
        self.assertEqual(
            set(model_admin.get_actions(request)), {'delete_selected', 'start_assessment', 'finish_assessment'}
        )

    def test__media_admin__edit_loads_full_object_without_deadline(self):
        model_admin = admin.site._registry[Media]
        request = self.get_request('admin:assessment_media_change', self.media[0].pk)

        with self.assertNumQueries(1):
            obj = model_admin.get_object(request, str(self.media[0].pk))
            form = model_admin.get_form(request, obj)(instance=obj)
            description = form.initial['description']
            meta_mark = form.initial['meta_mark']

        self.assertEqual(description, 'Description')
        self.assertEqual(meta_mark, Decimal('7.5'))
        self.assertNotIn('assessment_until_dt', form.fields)
        self.assertNotIn('assessment_until_dt', form.initial)

    def test__assessment_admin__edit_loads_review_without_deferred_queries(self):
        model_admin = admin.site._registry[Assessment]
        request = self.get_request('admin:assessment_assessment_change', self.assessment.pk)

        with self.assertNumQueries(1):
            obj = model_admin.get_object(request, str(self.assessment.pk))
            form = model_admin.get_form(request, obj)(instance=obj)
            review = form.initial['review']

        self.assertEqual(review, 'Admin review')
        self.assertFalse(form.fields['review'].required)
        self.assertEqual(form.fields['review'].max_length, 1000)

    def test__assessment_admin__list_columns_unchanged(self):
        model_admin = admin.site._registry[Assessment]
        request = self.get_request('admin:assessment_assessment_changelist')
        changelist = model_admin.get_changelist_instance(request)

        with self.assertNumQueries(1):
            rows = [
                (
                    obj.pk,
                    obj.mark,
                    obj.partial,
                    obj.create_dt,
                    model_admin.display_media(obj),
                    model_admin.display_user(obj),
                )
                for obj in changelist.result_list
            ]

        self.assertEqual(len(rows), 1)
        self.assertEqual(
            model_admin.get_list_display(request),
            (
                'id',
                'mark',
                'partial',
                'create_dt',
                'display_media',
                'display_user',
            ),
        )

    def test__assessment_admin__non_changelist_queryset_loads_full_models(self):
        request = RequestFactory().get('/')
        request.user = self.user
        for model in (Media, Assessment):
            with self.subTest(model=model.__name__), self.assertNumQueries(1):
                rows = list(admin.site._registry[model].get_queryset(request))
                for row in rows:
                    self.assertFalse(row.get_deferred_fields())

    def test__media_admin__authenticated_edit_page(self):
        self.client.force_login(self.user)
        ContentType.objects.clear_cache()

        # Session, user, Media, content type, category choices, creator choices.
        with self.assertNumQueries(6):
            response = self.client.get(reverse('admin:assessment_media_change', args=[self.media[0].pk]))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'assessment_until_dt')
        self.assertContains(response, 'Description')

    def test__media_admin__errors__anonymous_cannot_edit(self):
        with self.assertNumQueries(0):
            response = self.client.get(reverse('admin:assessment_media_change', args=[self.media[0].pk]))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('admin:login')))
