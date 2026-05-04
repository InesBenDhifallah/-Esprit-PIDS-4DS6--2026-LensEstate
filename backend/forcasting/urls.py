from django.urls import path

from .forcasting import ForecastingView

urlpatterns = [
    path("forecasting/", ForecastingView.as_view(), name="forecasting"),
]

