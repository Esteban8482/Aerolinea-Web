from rest_framework.exceptions import APIException


class FlightNotFound(APIException):
    status_code = 404
    default_code = "flight_not_found"
    default_detail = "Vuelo no encontrado."


class FlightNotEditable(APIException):
    status_code = 400
    default_code = "flight_not_editable"
    default_detail = "Solo los vuelos en estado programado admiten modificación."


class FlightNotCancellable(APIException):
    status_code = 400
    default_code = "flight_not_cancellable"
    default_detail = "Solo los vuelos en estado programado pueden ser cancelados."


class DepartureInPast(APIException):
    status_code = 400
    default_code = "departure_in_past"
    default_detail = "La fecha y hora de salida deben ser posteriores al momento actual."


class UnauthorizedRoute(APIException):
    status_code = 400
    default_code = "unauthorized_route"
    default_detail = "Ruta no autorizada para este tipo de vuelo."


class SameOriginDestination(APIException):
    status_code = 400
    default_code = "same_origin_destination"
    default_detail = "El origen y el destino deben ser diferentes."


class FlightCodeExhausted(APIException):
    status_code = 503
    default_code = "flight_code_exhausted"
    default_detail = "Se ha agotado el rango de códigos de vuelo disponibles (máximo 9999)."


class CancellationReasonRequired(APIException):
    status_code = 400
    default_code = "cancellation_reason_required"
    default_detail = "Debes indicar el motivo de la cancelación del vuelo."


class InvalidFlightCost(APIException):
    status_code = 400
    default_code = "invalid_flight_cost"
    default_detail = "El costo por persona debe ser un valor positivo."


class RefundFailed(APIException):
    status_code = 500
    default_code = "refund_failed"
    default_detail = "Falla técnica durante el abono a las billeteras de los pasajeros afectados."
