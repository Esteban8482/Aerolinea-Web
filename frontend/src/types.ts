export interface Ciudad {
  id: number;
  nombre: string;
  codigo_pais: string;
  zona_horaria: string;
  es_capital_principal: boolean;
  origen_internacional: boolean;
  destino_internacional: boolean;
}

export interface Ruta {
  id: number;
  origen: Ciudad;
  destino: Ciudad;
  tipo_vuelo: "NACIONAL" | "INTERNACIONAL";
  duracion_min: number;
  activa: boolean;
}

export interface Vuelo {
  id: number;
  codigo_vuelo: string;
  tipo_vuelo: "NACIONAL" | "INTERNACIONAL";
  origen: string;
  destino: string;
  fecha_salida: string;
  hora_salida: string;
  salida_utc: string;
  tiempo_vuelo_min: number;
  fecha_llegada: string;
  hora_llegada: string;
  llegada_utc: string;
  costo_persona_economica: string;
  costo_persona_primera: string;
  capacidad_total: number;
  cupos_disponibles_primera: number;
  cupos_disponibles_economica: number;
  estado: "PROGRAMADO" | "REALIZADO" | "CANCELADO";
}

export interface VueloDetalle extends Vuelo {
  ruta: Ruta;
  cupos_primera_clase: number;
  cupos_economica: number;
  motivo_cancelacion?: string;
  cancelado_en?: string;
  creado_por?: string;
  creado_en?: string;
}

export interface SessionState {
  authenticated: boolean;
  role: "ROOT" | "ADMINISTRADOR" | "CLIENTE" | null;
  email?: string;
  is_email_verified?: boolean;
}

