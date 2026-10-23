// Se cambio la direccion para el arranque temporal para la demo de la iteracion 1, revertir.

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import HomeDemo from './home/HomeDemo'
import './styles.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <HomeDemo />
  </StrictMode>,
)