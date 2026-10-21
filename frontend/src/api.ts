import { Ciudad, Ruta, SessionState, Vuelo, VueloDetalle } from "./types";

let cachedCsrfToken: string | null = null;

export async function fetchCsrfToken(): Promise<string> {
  const res = await fetch("/api/v1/auth/csrf/", { credentials: "include" });
  if (!res.ok) {
    throw new Error("No se pudo obtener el token CSRF.");
  }
  const data = await res.json();
  cachedCsrfToken = data.csrf_token;
  return data.csrf_token;
}

async function request<T>(
  url: string,
  options: RequestInit = {}
): Promise<T> {
  const method = (options.method || "GET").toUpperCase();
  const headers = new Headers(options.headers || {});

  if (["POST", "PATCH", "PUT", "DELETE"].includes(method)) {
    if (!cachedCsrfToken) {
      await fetchCsrfToken();
    }
    if (cachedCsrfToken) {
      headers.set("X-CSRFToken", cachedCsrfToken);
    }
  }

  if (options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(url, {
    ...options,
    headers,
    credentials: "include",
  });

  const contentType = response.headers.get("content-type");
  const data = contentType && contentType.includes("application/json")
    ? await response.json()
    : null;

  if (!response.ok) {
    const errorMsg = data?.message || data?.code || `Error HTTP ${response.status}`;
    const err = new Error(errorMsg);
    (err as unknown as { responseData: unknown }).responseData = data;
    throw err;
  }

  return data as T;
}

export const api = {
  // Autenticación y sesión
  getSession: () => request<SessionState>("/api/v1/auth/session/"),
  login: async (email: string, password: string) => {
    await fetchCsrfToken();
    const res = await request<SessionState>("/api/v1/auth/login/", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    // Tras login exitoso, renovar CSRF token
    await fetchCsrfToken();
    return res;
  },
  logout: async () => {
    await request<{ status: string }>("/api/v1/auth/logout/", { method: "POST" });
    await fetchCsrfToken();
  },

  // Catálogos
  getCities: () => request<Ciudad[]>("/api/v1/flights/cities/"),
  getRoutes: () => request<Ruta[]>("/api/v1/flights/routes/"),

  // Vuelos
  getFlights: (estado?: string) => {
    const url = estado && estado !== "TODOS"
      ? `/api/v1/flights/?estado=${encodeURIComponent(estado)}`
      : "/api/v1/flights/";
    return request<Vuelo[]>(url);
  },
  getFlightDetail: (id: number) => request<VueloDetalle>(`/api/v1/flights/${id}/`),

  // CU-01: Programar vuelo
  createFlight: (payload: {
    origen_id: number;
    destino_id: number;
    fecha_salida: string;
    hora_salida: string;
    costo_persona_economica: string;
    costo_persona_primera?: string;
  }) =>
    request<VueloDetalle>("/api/v1/flights/", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  // CU-02: Editar vuelo programado
  updateFlight: (
    id: number,
    payload: {
      fecha_salida?: string;
      hora_salida?: string;
      costo_persona_economica?: string;
      costo_persona_primera?: string;
    }
  ) =>
    request<VueloDetalle>(`/api/v1/flights/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  // CU-03: Cancelar vuelo programado
  cancelFlight: (
    id: number,
    payload: {
      motivo: string;
      alternativa?: "REINTEGRO" | "REUBICACION";
    }
  ) =>
    request<VueloDetalle>(`/api/v1/flights/${id}/cancel/`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};

