from django.http import JsonResponse
from django.shortcuts import render
from .models import Order
from django.views.decorators.http import require_POST


@require_POST
def create_order(request):
    order = Order.objects.create()
    return JsonResponse({'order_id': order.order_id}, status=200)


def index(request):
    return render(request, 'index.html')

