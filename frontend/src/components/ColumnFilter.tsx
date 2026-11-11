import { useEffect, useRef, useState, type ReactNode } from 'react'

interface ColumnFilterProps {
  label: string
  /** true cuando el filtro de esta columna tiene un valor activo */
  active?: boolean
  /** Controles del filtro (input, select, etc.) */
  children: ReactNode
}

/**
 * Encabezado de columna con filtro desplegable.
 * El usuario hace clic en el título de la columna y aparece el control;
 * se cierra al hacer clic fuera. Muestra un indicador cuando el filtro está activo.
 */
export default function ColumnFilter({ label, active = false, children }: ColumnFilterProps) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onClickOutside = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [open])

  return (
    <th style={{ position: 'relative', whiteSpace: 'nowrap' }}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        style={{
          background: 'transparent',
          border: 'none',
          cursor: 'pointer',
          fontWeight: 700,
          color: 'inherit',
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.35rem',
          padding: 0,
          fontSize: 'inherit',
          fontFamily: 'inherit',
        }}
        title={open ? 'Cerrar filtro' : 'Filtrar por ' + label}
        aria-expanded={open}
      >
        {label}
        <span
          aria-hidden="true"
          style={{
            fontSize: '0.65rem',
            lineHeight: 1,
            color: active ? 'var(--color-primary, #4b0082)' : 'inherit',
            opacity: active ? 1 : 0.55,
          }}
        >
          {active ? '●' : '▼'}
        </span>
      </button>
      {open && (
        <div
          ref={ref}
          style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            background: '#fff',
            border: '1px solid var(--color-border, #ddd)',
            borderRadius: '6px',
            padding: '0.75rem',
            zIndex: 30,
            minWidth: '230px',
            boxShadow: '0 4px 14px rgba(0, 0, 0, 0.18)',
            textAlign: 'left',
          }}
        >
          <div style={{ marginBottom: '0.5rem', fontSize: '0.8rem', fontWeight: 700 }}>
            Filtrar: {label}
          </div>
          {children}
        </div>
      )}
    </th>
  )
}
