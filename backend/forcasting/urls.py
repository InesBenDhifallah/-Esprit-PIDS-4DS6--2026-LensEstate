from django.urls import path

from .forcasting import ForecastingView, AgentReportView

urlpatterns = [
    path("forecasting/", ForecastingView.as_view(), name="forecasting"),
    path("forecasting/agent/", AgentReportView.as_view(), name="forecasting_agent"),

]


