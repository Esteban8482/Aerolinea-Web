import { useEffect, useState, useCallback } from "react";
import { Ciudad, Ruta, SessionState, Vuelo, VueloDetalle } from "./types";
import { api, fetchCsrfToken } from "./api";
import { AuthBar } from "./components/AuthBar";
import { FlightList } from "./components/FlightList";
import { FlightForm } from "./components/FlightForm";
import { FlightEdit } from "./components/FlightEdit";
import { FlightCancel } from "./components/FlightCancel";

export function App() {
  const [session, setSession] = useState<SessionState | null>(null);
  const [cities, setCities] = useState<Ciudad[]>([]);
  const [routes, setRoutes] = useState<Ruta[]>([]);
  const [flights, setFlights] = useState<Vuelo[]>([]);
  const [filtroEstado, setFiltroEstado] = useState<string>("TODOS");

  const [view, setView] = useState<"LIST" | "CREATE" | "EDIT">("LIST");
  const [selectedFlight, setSelectedFlight] = useState<VueloDetalle | null>(null);
  const [flightToCancel, setFlightToCancel] = useState<Vuelo | null>(null);

  const [loading, setLoading] = useState(false);
  const [notification, setNotification] = useState<string | null>(null);

  // Inicialización
  useEffect(() => {
    fetchCsrfToken().catch(() => {});
    api.getSession().then(setSession).catch(() => {});
    api.getCities().then(setCities).catch(() => {});
    api.getRoutes().then(setRoutes).catch(() => {});
  }, []);

  const loadFlights = useCallback(() => {
    setLoading(true);
    api.getFlights(filtroEstado)
      .then(setFlights)
      .catch((err) => {
        setNotification(err instanceof Error ? err.message : "Error al cargar vuelos.");
      })
      .finally(() => setLoading(false));
  }, [filtroEstado]);

  useEffect(() => {
    loadFlights();
  }, [loadFlights]);

  const handleOpenEdit = async (flight: Vuelo) => {
    try {
      const detail = await api.getFlightDetail(flight.id);
      setSelectedFlight(detail);
      setView("EDIT");
    } catch (err) {
      setNotification(err instanceof Error ? err.message : "Error al cargar detalle del vuelo.");
    }
  };

  const handleFlightCreated = () => {
    setView("LIST");
    setNotification("¡Vuelo programado exitosamente (CU-01)! Código y sillas generadas.");
    loadFlights();
  };

  const handleFlightUpdated = () => {
    setView("LIST");
    setSelectedFlight(null);
    setNotification("¡Vuelo editado exitosamente (CU-02)! Horarios de llegada recalculados.");
    loadFlights();
  };

  const handleFlightCancelled = () => {
    setFlightToCancel(null);
    setNotification("¡Vuelo cancelado exitosamente (CU-03)! Notificaciones registradas.");
    loadFlights();
  };

  const isAdmin = Boolean(session?.authenticated && session.role === "ADMINISTRADOR");

  return (
    <div className="container">
      <AuthBar session={session} onSessionChange={(s) => { setSession(s); loadFlights(); }} />

      {notification && (
        <div className="alert alert-success" style={{ display: "flex", justifyContent: "space-between" }}>
          <span>{notification}</span>
          <button
            onClick={() => setNotification(null)}
            style={{ background: "transparent", border: "none", cursor: "pointer", fontWeight: "bold" }}
          >
            ✕
          </button>
        </div>
      )}

      {view === "CREATE" ? (
        <FlightForm
          cities={cities}
          routes={routes}
          onFlightCreated={handleFlightCreated}
          onCancel={() => setView("LIST")}
        />
      ) : view === "EDIT" && selectedFlight ? (
        <FlightEdit
          flight={selectedFlight}
          onFlightUpdated={handleFlightUpdated}
          onCancel={() => {
            setView("LIST");
            setSelectedFlight(null);
          }}
        />
      ) : (
        <FlightList
          flights={flights}
          filtroEstado={filtroEstado}
          onFiltroChange={setFiltroEstado}
          onOpenCreate={() => setView("CREATE")}
          onOpenEdit={handleOpenEdit}
          onOpenCancel={setFlightToCancel}
          isAdmin={isAdmin}
          loading={loading}
        />
      )}

      {flightToCancel && (
        <FlightCancel
          flight={flightToCancel}
          onFlightCancelled={handleFlightCancelled}
          onCancel={() => setFlightToCancel(null)}
        />
      )}
    </div>
  );
}

