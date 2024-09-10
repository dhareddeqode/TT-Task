import threading
import traceback
from concurrent.futures import ThreadPoolExecutor

from django import db
from django.core.cache import cache
from django.db import transaction
from django.test import TransactionTestCase
from django.urls import reverse
from freezegun import freeze_time

from .models import Order


class DBSafeThreadPoolExecutor(ThreadPoolExecutor):
    def generate_initializer(self, initializer):
        def new_initializer(*args, **kwargs):
            self, *args = args
            try:
                if initializer != None:
                    initializer(*args, **kwargs)
            finally:
                self.on_thread_init()

        return new_initializer

    def on_thread_init(self):
        for curr_conn in db.connections.all():
            curr_conn.connection = None
            self.threads_db_conns.append(curr_conn)

    def on_executor_shutdown(self):
        [t.join() for t in self._threads if t != threading.current_thread()]
        for curr_conn in self.threads_db_conns:
            try:
                curr_conn.inc_thread_sharing()
                curr_conn.close()
            except Exception:
                print(f"error while closing connection {curr_conn.alias}")
                traceback.print_exc()

    def __init__(self, *args, **kwargs):
        kwargs["initializer"] = self.generate_initializer(kwargs.get("initializer"))
        kwargs["initargs"] = (self,) + (kwargs.get("initargs") or ())
        self.threads_db_conns = []
        super().__init__(*args, **kwargs)

    def shutdown(self, *args, **kwargs):
        self.submit(self.on_executor_shutdown)
        super().shutdown(*args, **kwargs)


class OrdersTest(TransactionTestCase):
    def setUp(self):
        cache.clear()

    @freeze_time("2024-05-03 10:00:00")
    def test_create_orders_for_the_day(self):
        """Test that the first order on the first day is correctly generated."""
        response = self.client.post(reverse("create_order"))
        self.assertEqual(response.status_code, 200)
        order_id = response.json()["order_id"]
        self.assertEqual(order_id, "20240503-00001")
        self.assertEqual(Order.objects.count(), 1)

        response = self.client.post(reverse("create_order"))
        self.assertEqual(response.status_code, 200)
        order_id = response.json()["order_id"]
        self.assertEqual(order_id, "20240503-00002")
        self.assertEqual(Order.objects.count(), 2)

    @freeze_time("2024-05-05 10:00:00")
    def test_create_orders_for_two_days(self):
        with freeze_time("2024-05-04 10:00:00"):
            self.client.post(reverse("create_order"))
            self.client.post(reverse("create_order"))
        response = self.client.post(reverse("create_order"))
        self.assertEqual(response.status_code, 200)
        order_id = response.json()["order_id"]
        self.assertEqual(order_id, "20240505-00001")
        self.assertEqual(Order.objects.count(), 3)

    @freeze_time("2024-05-06 10:00:00")
    def test_create_orders_after_cache_reset(self):
        self.client.post(reverse("create_order"))
        cache.clear()
        response = self.client.post(reverse("create_order"))
        self.assertEqual(response.status_code, 200)
        order_id = response.json()["order_id"]
        self.assertEqual(order_id, "20240506-00002")
        self.assertEqual(Order.objects.count(), 2)

    @freeze_time("2024-02-01 10:00:00")
    def test_concurrent_order_generation(self):
        def send_request():
            with transaction.atomic():
                response = self.client.post(reverse("create_order"))
                return response.json()["order_id"]

        order_count = 20

        with DBSafeThreadPoolExecutor(max_workers=order_count) as executor:
            futures = [executor.submit(send_request) for _ in range(order_count)]
            [future.result() for future in futures]

        self.assertEqual(Order.objects.count(), order_count)
        order_keys = [f"20240201-{i + 1:05d}" for i in range(order_count)]
        orders = Order.objects.filter(order_id__in=order_keys)
        self.assertEqual(orders.count(), order_count)
