import discord

from api.assessment.models import Media, MediaCategory
from bot.tests.media_modal_base import MediaModalBaseTestCase, media_modal_payload, submit_media_modal


class MediaModalAssessmentTestCase(MediaModalBaseTestCase):
    def test__media_modal__staff_checkbox(self):
        modal = self.get_modal()

        self.assertEqual(len(modal.children), 4)
        self.assertIsInstance(modal.children[-1], discord.ui.Label)
        self.assertIs(modal.children[-1].component, modal.move_to_assessment)
        self.assertTrue(modal.move_to_assessment.default)
        self.assertEqual(
            modal.to_dict()['components'][-1],
            {
                'type': discord.ComponentType.label.value,
                'label': modal.message_move_to_assessment,
                'component': {
                    'type': discord.ComponentType.checkbox.value,
                    'custom_id': modal.move_to_assessment.custom_id,
                    'default': True,
                },
            },
        )
        self.assertEqual(set(modal.get_form().fields), {'name', 'url', 'description', 'category'})

    def test__media_modal__regular_fields_unchanged(self):
        modal = self.get_modal(user=self.regular_user)

        self.assertIsNone(modal.move_to_assessment)
        self.assertEqual(modal.children, [modal.name, modal.url, modal.description])
        self.assertEqual(modal.title, f'Add a future {self.category.name.lower()}')
        components = modal.to_dict()['components']
        self.assertEqual([row['components'][0]['label'] for row in components], ['Name', 'URL', 'Description'])
        self.assertEqual([field.required for field in modal.children], [True, True, False])
        self.assertEqual([field.min_length for field in modal.children], [1, 1, None])
        self.assertEqual(
            [field.max_length for field in modal.children],
            [Media._meta.get_field('name').max_length, Media._meta.get_field('url').max_length, None],
        )
        self.assertEqual(modal.url.placeholder, Media._meta.get_field('url').help_text)
        self.assertEqual(modal.description.placeholder, Media._meta.get_field('description').help_text)
        self.assertEqual(modal.description.style, discord.TextStyle.long)
        self.assertEqual(len(components), 3)

    def test__media_modal__staff_default_creates_open_media(self):
        modal = self.get_modal()

        self.submit(modal)

        self.assert_saved(modal, Media.AssessmentStatus.IN_PROGRESS)
        self.search_mock.assert_awaited_once_with(title=self.name)

    def test__media_modal__staff_checked_creates_open_media(self):
        modal = self.get_modal()

        self.submit(modal, checked=True)

        self.assert_saved(modal, Media.AssessmentStatus.IN_PROGRESS)
        self.search_mock.assert_awaited_once_with(title=self.name)

    def test__media_modal__staff_unchecked_creates_future_media(self):
        modal = self.get_modal()

        self.submit(modal, checked=False)

        self.assert_saved(modal, Media.AssessmentStatus.INITIAL)
        self.search_mock.assert_awaited_once_with(title=self.name)

    def test__media_modal__regular_user_creates_future_media(self):
        modal = self.get_modal(user=self.regular_user)

        self.submit(modal)

        self.assert_saved(modal, Media.AssessmentStatus.INITIAL)
        self.search_mock.assert_awaited_once_with(title=self.name)

    def test__media_modal__errors__regular_forged_checkbox(self):
        modal = self.get_modal(user=self.regular_user)
        modal.move_to_assessment = discord.ui.Checkbox(default=True)
        components = media_modal_payload(modal, checked=True)

        with self.assertNumQueries(3):
            submit_media_modal(modal, self.interaction, components)

        self.assert_saved(modal, Media.AssessmentStatus.INITIAL)
        self.search_mock.assert_awaited_once_with(title=self.name)

    def test__media_modal__errors__superuser_without_staff(self):
        self.regular_user.is_superuser = True
        modal = self.get_modal(user=self.regular_user)
        self.assertIsNone(modal.move_to_assessment)

        self.submit(modal)

        self.assert_saved(modal, Media.AssessmentStatus.INITIAL)

    def test__media_modal__staff_missing_checkbox_creates_future_media(self):
        modal = self.get_modal()
        modal.remove_item(modal.children[-1])
        modal.move_to_assessment = None

        self.submit(modal)

        self.assert_saved(modal, Media.AssessmentStatus.INITIAL)

    def test__media_modal__staff_status_from_invocation(self):
        modal = self.get_modal()
        type(self.user).objects.filter(pk=self.user.pk).update(is_staff=False)

        self.submit(modal)

        self.assert_saved(modal, Media.AssessmentStatus.IN_PROGRESS)

    def test__media_modal__checkbox_state_isolated(self):
        first = self.get_modal()
        second = self.get_modal()

        first._refresh(self.interaction, media_modal_payload(first, checked=False), {})

        self.assertFalse(first.move_to_assessment.value)
        self.assertTrue(second.move_to_assessment.value)
        self.submit(second)
        self.assert_saved(second, Media.AssessmentStatus.IN_PROGRESS)

    def test__media_modal__unsupported_meta_mark_category(self):
        modal = self.get_modal(category=MediaCategory.objects.game())

        self.submit(modal)

        self.assert_saved(modal, Media.AssessmentStatus.IN_PROGRESS, meta_mark=None)
        self.search_mock.assert_not_awaited()
