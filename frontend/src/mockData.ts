export type Flight = {
  id: string
  code: string
  type: 'Nacional' | 'Internacional'
  origin: string
  originCode: string
  destination: string
  destinationCode: string
  departure: string
  duration: string
  price: number
  capacity: number
  available: number
  status: 'Programado' | 'Agotado'
  promotion?: string
}

export type PaymentMethod = {
  id: string
  type: 'Tarjeta' | 'Cuenta bancaria'
  label: string
  lastFour: string
}

export type WalletMovement = {
  id: string
  date: string
  type: 'Depósito' | 'Compra'
  method: string
  amount: number
  balance: number
}

export const cities = [
  { code: 'BOG', name: 'Bogotá' },
  { code: 'CLO', name: 'Cali' },
  { code: 'CTG', name: 'Cartagena' },
  { code: 'MDE', name: 'Medellín' },
  { code: 'PEI', name: 'Pereira' },
  { code: 'MAD', name: 'Madrid' },
  { code: 'MIA', name: 'Miami' },
  { code: 'JFK', name: 'Nueva York' },
]

export const initialFlights: Flight[] = [
  {
    id: '1',
    code: 'ALA-001',
    type: 'Nacional',
    origin: 'Pereira',
    originCode: 'PEI',
    destination: 'Bogotá',
    destinationCode: 'BOG',
    departure: '2026-12-10T07:30',
    duration: '1h 05min',
    price: 245000,
    capacity: 150,
    available: 82,
    status: 'Programado',
  },
  {
    id: '2',
    code: 'ALA-014',
    type: 'Nacional',
    origin: 'Medellín',
    originCode: 'MDE',
    destination: 'Cartagena',
    destinationCode: 'CTG',
    departure: '2026-12-12T14:00',
    duration: '1h 10min',
    price: 318000,
    capacity: 150,
    available: 24,
    status: 'Programado',
    promotion: '10% de descuento',
  },
  {
    id: '3',
    code: 'ALA-101',
    type: 'Internacional',
    origin: 'Pereira',
    originCode: 'PEI',
    destination: 'Madrid',
    destinationCode: 'MAD',
    departure: '2026-12-18T21:15',
    duration: '9h 35min',
    price: 1249000,
    capacity: 250,
    available: 117,
    status: 'Programado',
  },
  {
    id: '4',
    code: 'ALA-205',
    type: 'Internacional',
    origin: 'Bogotá',
    originCode: 'BOG',
    destination: 'Miami',
    destinationCode: 'MIA',
    departure: '2026-12-20T09:45',
    duration: '3h 50min',
    price: 890000,
    capacity: 250,
    available: 0,
    status: 'Agotado',
  },
]

const flightsKey = 'alas-iteration-2-flights'
const walletKey = 'alas-iteration-2-wallet'

export function loadFlights(): Flight[] {
  const saved = localStorage.getItem(flightsKey)
  if (!saved) return initialFlights
  try {
    return JSON.parse(saved) as Flight[]
  } catch {
    return initialFlights
  }
}

export function saveFlights(flights: Flight[]) {
  localStorage.setItem(flightsKey, JSON.stringify(flights))
}

export type WalletState = {
  balance: number
  methods: PaymentMethod[]
  movements: WalletMovement[]
}

export const initialWallet: WalletState = {
  balance: 350000,
  methods: [
    { id: 'card-1', type: 'Tarjeta', label: 'Visa débito', lastFour: '4821' },
  ],
  movements: [
    {
      id: 'movement-1',
      date: '2026-11-02T10:30',
      type: 'Depósito',
      method: 'Visa débito •••• 4821',
      amount: 350000,
      balance: 350000,
    },
  ],
}

export function loadWallet(): WalletState {
  const saved = localStorage.getItem(walletKey)
  if (!saved) return initialWallet
  try {
    return JSON.parse(saved) as WalletState
  } catch {
    return initialWallet
  }
}

export function saveWallet(wallet: WalletState) {
  localStorage.setItem(walletKey, JSON.stringify(wallet))
}

export function formatCurrency(value: number) {
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    maximumFractionDigits: 0,
  }).format(value)
}

export function formatDate(value: string) {
  return new Intl.DateTimeFormat('es-CO', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}
