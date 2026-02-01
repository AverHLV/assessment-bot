from django.contrib import admin
from django.urls import path
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(url='/admin/'), name='home'),
    path('admin/', admin.site.urls),
]
