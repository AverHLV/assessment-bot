from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse

from api.mcp.models import OAuthClient, OAuthNonce
from api.mcp.tests.factories import OAuthClientFactory, OAuthNonceFactory
from api.user.tests.factories import UserFactory


class OAuthAdminTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.administrator = UserFactory(is_staff=True, is_superuser=True)
        cls.non_staff = UserFactory(is_staff=False)
        cls.staff_without_permissions = UserFactory(is_staff=True, is_superuser=False)
        cls.viewer = UserFactory(is_staff=True, is_superuser=False)
        cls.viewer.user_permissions.add(
            *Permission.objects.filter(content_type__app_label='mcp', codename__startswith='view_')
        )
        cls.clients = OAuthClientFactory.create_batch(3)
        cls.code_nonce = OAuthNonceFactory(purpose=OAuthNonce.Purpose.AUTHORIZATION_CODE, consumed=False)
        cls.consumed_nonce = OAuthNonceFactory(purpose=OAuthNonce.Purpose.AUTHORIZATION_CODE, consumed=True)
        cls.state_nonce = OAuthNonceFactory(purpose=OAuthNonce.Purpose.DISCORD_STATE, consumed=False)

    def setUp(self):
        self.client.force_login(self.administrator)

    def admin_url(self, model, action='changelist', obj=None):
        name = f'admin:{model._meta.app_label}_{model._meta.model_name}_{action}'
        return reverse(name, args=[obj.pk] if obj is not None else None)

    def test__oauth_admin__models_in_index(self):
        # Session, authenticated user, and Django admin's recent-action history.
        with self.assertNumQueries(3):
            response = self.client.get(reverse('admin:index'))

        self.assertEqual(response.status_code, 200)
        for model in (OAuthClient, OAuthNonce):
            self.assertContains(response, self.admin_url(model))

    def test__oauth_admin__client_and_nonce_lists(self):
        cases = (
            (OAuthClient, {obj.pk for obj in self.clients}),
            (OAuthNonce, {self.code_nonce.pk, self.consumed_nonce.pk, self.state_nonce.pk}),
        )
        for model, expected in cases:
            with self.subTest(model=model.__name__), self.assertNumQueries(4):
                response = self.client.get(self.admin_url(model))

            self.assertEqual(response.status_code, 200)
            self.assertEqual({obj.pk for obj in response.context['cl'].result_list}, expected)
            if model is OAuthClient:
                self.assertTrue(
                    all(
                        obj.get_deferred_fields() == {'metadata', 'secret_digest'}
                        for obj in response.context['cl'].result_list
                    )
                )
            else:
                self.assertEqual(
                    response.context['cl'].list_display,
                    ['action_checkbox', 'digest', 'purpose', 'expires_at', 'consumed'],
                )

    def test__oauth_admin__detail_forms_load_full_records(self):
        for obj in (self.clients[0], self.code_nonce):
            ContentType.objects.clear_cache()

            with self.subTest(model=type(obj).__name__), self.assertNumQueries(4):
                response = self.client.get(self.admin_url(type(obj), 'change', obj))

            self.assertEqual(response.status_code, 200)
            form = response.context['adminform'].form
            self.assertFalse(form.instance.get_deferred_fields())
            if isinstance(obj, OAuthClient):
                self.assertEqual(form.initial['metadata'], obj.metadata)
                self.assertEqual(form.initial['secret_digest'], obj.secret_digest)
            else:
                self.assertEqual(form.initial['digest'], obj.digest)
                self.assertEqual(form.initial['purpose'], obj.purpose)
                self.assertFalse(form.initial['consumed'])

    def test__oauth_admin__identifier_search(self):
        for obj in (self.clients[1], self.consumed_nonce):
            with self.subTest(model=type(obj).__name__), self.assertNumQueries(4):
                response = self.client.get(self.admin_url(type(obj)), {'q': obj.pk})

            self.assertEqual(response.status_code, 200)
            self.assertEqual([item.pk for item in response.context['cl'].result_list], [obj.pk])

    def test__oauth_admin__nonce_filters(self):
        for params, expected in (
            ({'purpose__exact': OAuthNonce.Purpose.DISCORD_STATE}, {self.state_nonce.pk}),
            ({'consumed__exact': '1'}, {self.consumed_nonce.pk}),
            ({'purpose__exact': OAuthNonce.Purpose.AUTHORIZATION_CODE, 'consumed__exact': '0'}, {self.code_nonce.pk}),
        ):
            with self.subTest(params=params), self.assertNumQueries(4):
                response = self.client.get(self.admin_url(OAuthNonce), params)

            self.assertEqual(response.status_code, 200)
            self.assertEqual({obj.pk for obj in response.context['cl'].result_list}, expected)

    def test__oauth_admin__errors__anonymous(self):
        self.client.logout()
        for obj in (self.clients[0], self.code_nonce):
            for action in ('changelist', 'change'):
                with self.subTest(model=type(obj).__name__, action=action), self.assertNumQueries(0):
                    response = self.client.get(self.admin_url(type(obj), action, obj if action == 'change' else None))

                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.url.startswith(reverse('admin:login')))

    def test__oauth_admin__staff_with_view_permissions(self):
        self.client.force_login(self.viewer)
        for obj in (self.clients[0], self.code_nonce):
            for action in ('changelist', 'change'):
                ContentType.objects.clear_cache()

                with self.subTest(model=type(obj).__name__, action=action), self.assertNumQueries(6):
                    response = self.client.get(self.admin_url(type(obj), action, obj if action == 'change' else None))

                self.assertEqual(response.status_code, 200)

    def test__oauth_admin__errors__non_staff(self):
        self.client.force_login(self.non_staff)
        for obj in (self.clients[0], self.code_nonce):
            for action in ('changelist', 'change'):
                with self.subTest(model=type(obj).__name__, action=action), self.assertNumQueries(2):
                    response = self.client.get(self.admin_url(type(obj), action, obj if action == 'change' else None))

                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.url.startswith(reverse('admin:login')))

    def test__oauth_admin__errors__staff_without_permissions(self):
        self.client.force_login(self.staff_without_permissions)
        for obj in (self.clients[0], self.code_nonce):
            for action in ('changelist', 'change'):
                # Detail requests resolve the row before checking its object-level model permission.
                count = 5 if action == 'change' else 4
                with self.subTest(model=type(obj).__name__, action=action), self.assertNumQueries(count):
                    response = self.client.get(self.admin_url(type(obj), action, obj if action == 'change' else None))

                self.assertEqual(response.status_code, 403)
