from django.db import close_old_connections, connection
from django.test import TransactionTestCase

from asgiref.sync import async_to_sync

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from api.mcp.managers import digest
from api.mcp.models import OAuthNonce
from api.mcp.tests.factories import OAuthNonceFactory


# The plan explicitly requires committed rows and independent PostgreSQL connections for this race.
class ReplayTestCase(TransactionTestCase):
    def test__nonce__one_winner_on_independent_connections(self):
        for purpose in OAuthNonce.Purpose.values:
            with self.subTest(purpose=purpose):
                nonce = f'nonce-{purpose}'
                OAuthNonceFactory(digest=digest(nonce), purpose=purpose)
                ready = Barrier(2)

                def consume(ready=ready, nonce=nonce, purpose=purpose):
                    close_old_connections()
                    try:
                        ready.wait(timeout=10)
                        with self.assertNumQueries(1):
                            return async_to_sync(OAuthNonce.objects.consume)(nonce, purpose)
                    finally:
                        connection.close()

                with ThreadPoolExecutor(max_workers=2) as executor:
                    results = list(executor.map(lambda _: consume(), range(2)))

                self.assertEqual(sorted(results), [False, True])
                self.assertTrue(OAuthNonce.objects.get(pk=digest(nonce)).consumed)
