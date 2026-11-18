from django.urls import path

from .views import (
    PurchaseCancelView,
    PurchaseDetailView,
    PurchaseListCreateView,
    ReservationCancelView,
    ReservationDetailView,
    ReservationListCreateView,
    SearchHistoryView,
    SeatMapView,
    TicketSeatChangeView,
)

urlpatterns = [
    path(
        "reservations/",
        ReservationListCreateView.as_view(),
        name="sales-reservations-list-create",
    ),
    path(
        "reservations/<int:pk>/",
        ReservationDetailView.as_view(),
        name="sales-reservations-detail",
    ),
    path(
        "reservations/<int:pk>/cancel/",
        ReservationCancelView.as_view(),
        name="sales-reservations-cancel",
    ),
    path("purchases/", PurchaseListCreateView.as_view(), name="sales-purchases-list-create"),
    path("purchases/<int:pk>/", PurchaseDetailView.as_view(), name="sales-purchases-detail"),
    path(
        "purchases/<int:pk>/cancel/",
        PurchaseCancelView.as_view(),
        name="sales-purchases-cancel",
    ),
    path("flights/<int:vuelo_id>/seats/", SeatMapView.as_view(), name="sales-seat-map"),
    path(
        "tickets/<int:pk>/change-seat/",
        TicketSeatChangeView.as_view(),
        name="sales-ticket-change-seat",
    ),
    path("search-history/", SearchHistoryView.as_view(), name="sales-search-history"),
]
