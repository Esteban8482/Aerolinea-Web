export interface Ciudad {
  id: number
  nombre: string
  codigo_pais: string
  zona_horaria: string
  es_capital_principal: boolean
  origen_internacional: boolean
  destino_internacional: boolean
}

export interface Ruta {
  id: number
  origen: Ciudad
  destino: Ciudad
  tipo_vuelo: 'NACIONAL' | 'INTERNACIONAL'
  duracion_min: number
  activa: boolean
}

export interface Vuelo {
  id: number
  codigo_vuelo: string
  tipo_vuelo: 'NACIONAL' | 'INTERNACIONAL'
  origen: string
  destino: string
  fecha_salida: string
  hora_salida: string
  salida_utc: string
  tiempo_vuelo_min: number
  fecha_llegada: string
  hora_llegada: string
  llegada_utc: string
  costo_persona_economica: string
  costo_persona_primera: string
  capacidad_total: number
  cupos_disponibles_primera: number
  cupos_disponibles_economica: number
  estado: 'PROGRAMADO' | 'REALIZADO' | 'CANCELADO'
}

export interface VueloDetalle extends Vuelo {
  ruta: Ruta
  cupos_primera_clase: number
  cupos_economica: number
  motivo_cancelacion?: string
  cancelado_en?: string
  creado_por?: string
  creado_en?: string
  actualizado_en?: string
}

export interface Silla {
  id: number
  numero_silla: number
  clase: 'PRIMERA_CLASE' | 'ECONOMICA'
  estado: 'DISPONIBLE' | 'RESERVADA' | 'OCUPADA'
  espacio_extra: boolean
}

export interface Viajero {
  id?: number
  documento: string
  tipo_documento?: string
  nombres: string
  apellidos: string
  fecha_nacimiento: string
  genero?: string
  telefono?: string
  correo: string
  nombre_contacto?: string
  telefono_contacto?: string
}

export interface Reserva {
  id: number
  vuelo: Vuelo
  vuelo_regreso?: Vuelo | null
  tipo_trayecto: 'UNICO' | 'COMPLETO'
  clase: 'PRIMERA_CLASE' | 'ECONOMICA'
  limite_vigencia: string
  estado: 'VIGENTE' | 'COMPRADA' | 'VENCIDA' | 'CANCELADA'
  creada_en: string
  viajeros: Viajero[]
}

export interface Tiquete {
  id: number
  codigo_tiquete: string
  vuelo: Vuelo
  viajero: Viajero
  silla: Silla
  clase: 'PRIMERA_CLASE' | 'ECONOMICA'
  precio_pagado: string
  numero_cambios_silla: number
  estado_checkin: 'PENDIENTE' | 'CONFIRMADO'
  fecha_checkin?: string | null
  estado: 'ACTIVO' | 'CANCELADO'
}

export interface Compra {
  id: number
  localizador: string
  valor_pagado: string
  tipo_trayecto: 'UNICO' | 'COMPLETO'
  estado: 'CONFIRMADA' | 'CANCELADA'
  fecha_compra: string
  fecha_cancelacion?: string | null
  tiquetes: Tiquete[]
}

export interface PerfilUsuario {
  id: number
  username: string
  email: string
  first_name: string
  last_name: string
  document_number: string
  document_type: string
  birth_date: string | null
  birth_place: string | null
  billing_address: string | null
  gender: string | null
  role: string
  is_email_verified: boolean
  wallet_balance: string
}


