from rest_framework.exceptions import APIException


class ReservationWindowClosed(APIException):
    status_code = 400
    default_code = "reservation_window_closed"
    default_detail = (
        "Ya no es posible realizar reservas para este vuelo debido a la proximidad de la salida."
    )


class FlightNotAvailableForSale(APIException):
    status_code = 400
    default_code = "flight_not_available_for_sale"
    default_detail = "El vuelo no se encuentra disponible para venta o reserva."


class InsufficientSeats(APIException):
    status_code = 400
    default_code = "insufficient_seats"
    default_detail = "No hay cupos suficientes disponibles en la clase seleccionada."


class TicketLimitExceeded(APIException):
    status_code = 400
    default_code = "ticket_limit_exceeded"
    default_detail = (
        "Un cliente no puede superar el límite de 5 tiquetes activos para el mismo vuelo."
    )


class AdultPassengerRequired(APIException):
    status_code = 400
    default_code = "adult_passenger_required"
    default_detail = "Al menos un viajero debe ser mayor de edad en la fecha del vuelo."


class DuplicatePassengerInFlight(APIException):
    status_code = 400
    default_code = "duplicate_passenger_in_flight"
    default_detail = "Una misma persona no puede figurar duplicada como viajero en el mismo vuelo."


class ReservationNotActive(APIException):
    status_code = 400
    default_code = "reservation_not_active"
    default_detail = "La reserva no está vigente o ya fue utilizada o cancelada."


class CancellationWindowClosed(APIException):
    status_code = 400
    default_code = "cancellation_window_closed"
    default_detail = "Se ha superado el plazo límite permitido para cancelar esta operación."


class SeatNotAvailable(APIException):
    status_code = 400
    default_code = "seat_not_available"
    default_detail = (
        "La silla seleccionada no está disponible o no pertenece a la clase del tiquete."
    )


class SeatChangeLimitReached(APIException):
    status_code = 400
    default_code = "seat_change_limit_reached"
    default_detail = "El tiquete ya ha alcanzado el límite máximo de un cambio de silla permitido."


class CheckinAlreadyConfirmed(APIException):
    status_code = 400
    default_code = "checkin_already_confirmed"
    default_detail = "No es posible cambiar de silla debido a que el check-in ya fue confirmado."


class PurchaseNotCancellable(APIException):
    status_code = 400
    default_code = "purchase_not_cancellable"
    default_detail = "La compra no se encuentra en estado cancelable."
