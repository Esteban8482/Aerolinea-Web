import React, { useState, useMemo } from "react";
import { Ciudad, Ruta } from "../types";
import { api } from "../api";

interface FlightFormProps {
  cities: Ciudad[];
  routes: Ruta[];
  onFlightCreated: () => void;
  onCancel: () => void;
}

export const FlightForm: React.FC<FlightFormProps> = ({
  cities,
  routes,
  onFlightCreated,
  onCancel,
}) => {
  const [tipoVuelo, setTipoVuelo] = useState<"NACIONAL" | "INTERNACIONAL">("NACIONAL");
  const [origenId, setOrigenId] = useState<number>(0);
  const [destinoId, setDestinoId] = useState<number>(0);
  const [fechaSalida, setFechaSalida] = useState<string>("");
  const [horaSalida, setHoraSalida] = useState<string>("");
  const [costoEconomica, setCostoEconomica] = useState<string>("180000");
  const [costoPrimera, setCostoPrimera] = useState<string>("270000");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filtrado de ciudades según tipo de vuelo
  const origenesDisponibles = useMemo(() => {
    if (tipoVuelo === "NACIONAL") {
      return cities.filter((c) => c.es_capital_principal);
    }
    return cities.filter((c) => c.origen_internacional);
  }, [cities, tipoVuelo]);

  const destinosDisponibles = useMemo(() => {
    if (tipoVuelo === "NACIONAL") {
      return cities.filter((c) => c.es_capital_principal && c.id !== origenId);
    }
    return cities.filter((c) => c.destino_internacional);
  }, [cities, tipoVuelo, origenId]);

  // Ruta seleccionada y duración calculada
  const rutaSeleccionada = useMemo(() => {
    if (!origenId || !destinoId) return null;
    return routes.find((r) => r.origen.id === origenId && r.destino.id === destinoId);
  }, [routes, origenId, destinoId]);

  // Capacidad según reglas RN-12 y RN-13
  const capacidad = tipoVuelo === "NACIONAL" ? 150 : 250;
  const sillasPrimera = tipoVuelo === "NACIONAL" ? 25 : 50;
  const sillasEconomica = tipoVuelo === "NACIONAL" ? 125 : 200;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!origenId || !destinoId) {
      setError("Debes seleccionar una ciudad de origen y una de destino.");
      return;
    }
    if (!rutaSeleccionada) {
      setError("Ruta no autorizada para este tipo de vuelo.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      await api.createFlight({
        origen_id: origenId,
        destino_id: destinoId,
        fecha_salida: fechaSalida,
        hora_salida: horaSalida.length === 5 ? `${horaSalida}:00` : horaSalida,
        costo_persona_economica: costoEconomica,
        costo_persona_primera: costoPrimera || undefined,
      });
      onFlightCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al programar el vuelo.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">Programar nuevo vuelo (CU-01)</h2>
        <button className="btn o" onClick={onCancel}>
          ✕ Volver
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      <form onSubmit={handleSubmit}>
        <div className="grid-2">
          <label>
            Tipo de vuelo
            <select
              value={tipoVuelo}
              onChange={(e) => {
                setTipoVuelo(e.target.value as "NACIONAL" | "INTERNACIONAL");
                setOrigenId(0);
                setDestinoId(0);
              }}
            >
              <option value="NACIONAL">Nacional (Capitales principales)</option>
              <option value="INTERNACIONAL">Internacional (Rutas directas autorizadas)</option>
            </select>
          </label>

          <label>
            Ciudad de origen
            <select
              value={origenId || ""}
              onChange={(e) => setOrigenId(Number(e.target.value))}
              required
            >
              <option value="">Seleccione origen...</option>
              {origenesDisponibles.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nombre} ({c.codigo_pais})
                </option>
              ))}
            </select>
          </label>

          <label>
            Ciudad de destino
            <select
              value={destinoId || ""}
              onChange={(e) => setDestinoId(Number(e.target.value))}
              required
            >
              <option value="">Seleccione destino...</option>
              {destinosDisponibles.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nombre} ({c.codigo_pais})
                </option>
              ))}
            </select>
          </label>

          <label>
            Fecha de salida (local del origen)
            <input
              type="date"
              value={fechaSalida}
              onChange={(e) => setFechaSalida(e.target.value)}
              required
            />
          </label>

          <label>
            Hora de salida (local del origen)
            <input
              type="time"
              value={horaSalida}
              onChange={(e) => setHoraSalida(e.target.value)}
              required
            />
          </label>

          <label>
            Costo clase económica (COP)
            <input
              type="number"
              min="1000"
              step="1000"
              value={costoEconomica}
              onChange={(e) => {
                const val = e.target.value;
                setCostoEconomica(val);
                if (val && !isNaN(Number(val))) {
                  setCostoPrimera((Number(val) * 1.5).toFixed(2));
                }
              }}
              required
            />
          </label>

          <label>
            Costo primera clase (COP)
            <input
              type="number"
              min="1000"
              step="1000"
              value={costoPrimera}
              onChange={(e) => setCostoPrimera(e.target.value)}
              required
            />
          </label>
        </div>

        {/* Sección calculada por el sistema según el mockup */}
        <div className="calculated-box">
          <div className="calculated-box-title">Calculado automáticamente por el sistema</div>
          <div className="grid-3">
            <label>
              Código de vuelo
              <input disabled value="Autogenerado (XX0001 - XX9999)" />
            </label>
            <label>
              Duración estimada
              <input
                disabled
                value={
                  rutaSeleccionada
                    ? `${rutaSeleccionada.duracion_min} minutos`
                    : "Selecciona ruta válida"
                }
              />
            </label>
            <label>
              Capacidad total
              <input disabled value={`${capacidad} pasajeros`} />
            </label>
            <label>
              Sillas primera clase
              <input disabled value={`Sillas 1 a ${sillasPrimera}`} />
            </label>
            <label>
              Sillas económica
              <input disabled value={`Sillas ${sillasPrimera + 1} a ${capacidad} (${sillasEconomica} cupos)`} />
            </label>
            <label>
              Publicación automática
              <input disabled value="Noticia oficial alusiva" />
            </label>
          </div>
        </div>

        <div style={{ display: "flex", gap: "12px", marginTop: "16px" }}>
          <button className="btn" type="submit" disabled={loading}>
            {loading ? "Guardando vuelo..." : "Guardar vuelo"}
          </button>
          <button className="btn o" type="button" onClick={onCancel} disabled={loading}>
            Cancelar
          </button>
        </div>
      </form>
    </div>
  );
};
