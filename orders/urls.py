from django.urls import path

from orders import views

urlpatterns = [
    path("", views.index, name="index"),
    path("create-order/", views.create_order, name="create_order"),
]
