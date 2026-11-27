from django.urls import path

from .journey_views import (
    BoardingPassView,
    CheckinView,
    CompleteFlightView,
    FlightNewsView,
    GuestLinkView,
    GuestSeatView,
    PromotionsView,
    QuoteView,
    RelocationDecisionView,
    RelocationOffersView,
)
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


urlpatterns += [
    path("check-in/", CheckinView.as_view(), name="sales-checkin"),
    path("check-in/access/", GuestLinkView.as_view(), name="sales-guest-access"),
    path("check-in/tickets/<int:pk>/seat/", GuestSeatView.as_view(), name="sales-guest-seat"),
    path("tickets/<int:pk>/boarding-pass/", BoardingPassView.as_view(), name="sales-boarding-pass"),
    path("flights/<int:pk>/promotions/", PromotionsView.as_view(), name="sales-promotions"),
    path("relocations/", RelocationOffersView.as_view(), name="sales-relocations"),
    path(
        "relocations/<int:pk>/", RelocationDecisionView.as_view(), name="sales-relocation-decision"
    ),
]


urlpatterns += [path("quote/", QuoteView.as_view(), name="sales-quote")]

urlpatterns += [
    path(
        "flights/<int:pk>/performed/", CompleteFlightView.as_view(), name="sales-flight-performed"
    ),
    path("flight-news/", FlightNewsView.as_view(), name="sales-flight-news"),
]
