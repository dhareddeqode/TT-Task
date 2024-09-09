from datetime import datetime
from django.core.cache import cache
from django.db import models
from django.conf import settings
from django.db.utils import IntegrityError


class OrderManager(models.Manager):
    def bulk_create(self):
        pass


class Order(models.Model):
    order_id = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # rest order fields

    ORDER_KEY_FORMAT = "{today}-{sequence:05d}"

    def __str__(self):
        return self.order_id

    def save(
        self,
        *args,
        **kwargs
    ):
        if self.order_id:
            return super().save(*args, **kwargs)

        self.order_id = self.create_order_id()
        try:
            return super().save(*args, **kwargs)
        except IntegrityError:
            # If current date key not found in cache but orders exists, means cache is reset
            # get order sequence from db
            self.order_id = self.create_order_id(use_cache=False)
            try:
                return super().save(*args, **kwargs)
            except IntegrityError:
                # To handle the race condition (collision)
                self.order_id = self.create_order_id()
                return super().save(*args, **kwargs)

    @classmethod
    def create_order_id(cls, use_cache=True):
        today = datetime.now().strftime("%Y%m%d")
        key = f"order_sequence:{today}"
        if use_cache:
            sequence = cache.incr(key, ignore_key_check=True)
        else:
            sequence = cls.get_sequence_from_db()
            cache.set(key, sequence)
        cache.expire(key, settings.ORDER_SEQUENCE_EXPIRY)
        return cls.ORDER_KEY_FORMAT.format(today=today, sequence=sequence)

    @classmethod
    def get_sequence_from_db(cls):
        if order := cls.objects.filter(created_at__date=datetime.today()).latest("created_at"):
            return order.get_order_sequence + 1
        return 1

    @property
    def get_order_sequence(self):
        return int(self.order_id.split('-')[-1])

