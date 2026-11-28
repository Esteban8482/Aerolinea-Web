import { useEffect, useId, useRef, useState, type KeyboardEvent } from 'react'
import { api } from '../api'
import { ChevronDown } from 'lucide-react'

export interface Choice {
  id: number
  name?: string
  nombre?: string
  label?: string
}

interface Props {
  label: string
  endpoint: string | null
  value: Choice | null
  onChange: (value: Choice | null) => void
  onCount?: (count: number) => void
}

function choiceLabel(choice: Choice) {
  return choice.label ?? choice.name ?? choice.nombre ?? String(choice.id)
}

function nextPagePath(next: string) {
  const url = new URL(next, window.location.origin)
  const path = url.pathname.replace(/^\/api\/v1(?=\/)/, '')
  return `${path}${url.search}`
}

export default function RemoteSelect({
  label,
  endpoint,
  value,
  onChange,
  onCount,
}: Props) {
  const id = useId()
  const listboxId = `${id}-options`
  const rootRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const searchRef = useRef<HTMLInputElement>(null)
  const [retry, setRetry] = useState(0)
  const generation = useRef(0)
  const countCallback = useRef(onCount)
  const [query, setQuery] = useState('')
  const [rows, setRows] = useState<Choice[]>([])
  const [next, setNext] = useState<string | null>(null)
  const [activeIndex, setActiveIndex] = useState(-1)
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  countCallback.current = onCount

  useEffect(() => {
    setOpen(false)
    setQuery('')
    setActiveIndex(-1)
  }, [endpoint])

  useEffect(() => {
    const requestId = ++generation.current
    setRows([])
    setNext(null)
    setError('')
    if (!endpoint || !open) {
      setBusy(false)
      return
    }

    setBusy(true)
    const timer = window.setTimeout(() => {
      const separator = endpoint.includes('?') ? '&' : '?'
      api
        .get(`${endpoint}${separator}q=${encodeURIComponent(query)}`)
        .then((data) => {
          if (requestId !== generation.current) return
          setRows(data.results)
          setNext(data.next)
          setActiveIndex(-1)
          if (!query) countCallback.current?.(data.count)
        })
        .catch(() => {
          if (requestId === generation.current) {
            setError('No se pudieron cargar las opciones.')
          }
        })
        .finally(() => {
          if (requestId === generation.current) setBusy(false)
        })
    }, 250)

    return () => {
      window.clearTimeout(timer)
      generation.current++
    }
  }, [endpoint, open, query, retry])

  useEffect(() => {
    if (!open) return
    function closeOnOutsidePointer(event: PointerEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false)
        setQuery('')
        setActiveIndex(-1)
      }
    }
    document.addEventListener('pointerdown', closeOnOutsidePointer)
    return () =>
      document.removeEventListener('pointerdown', closeOnOutsidePointer)
  }, [open])

  async function loadMore() {
    if (!next || busy) return
    const requestId = generation.current
    setBusy(true)
    setError('')
    try {
      const data = await api.get(nextPagePath(next))
      if (requestId === generation.current) {
        setRows((current) => [...current, ...data.results])
        setNext(data.next)
      }
    } catch {
      if (requestId === generation.current) {
        setError('No se pudo cargar la siguiente página.')
      }
    } finally {
      if (requestId === generation.current) setBusy(false)
    }
  }

  useEffect(() => {
    if (open) searchRef.current?.focus()
  }, [open])

  useEffect(() => {
    if (activeIndex >= 0)
      document
        .getElementById(`${listboxId}-${rows[activeIndex]?.id}`)
        ?.scrollIntoView({ block: 'nearest' })
  }, [activeIndex, rows, listboxId])

  function choose(choice: Choice | null) {
    triggerRef.current?.focus()
    onChange(choice)
    setOpen(false)
    setQuery('')
    setActiveIndex(-1)
  }

  function handleKeyDown(
    event: KeyboardEvent<HTMLInputElement | HTMLButtonElement>,
  ) {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      if (!open) {
        setOpen(true)
        setActiveIndex(0)
      } else if (rows.length) {
        setActiveIndex((index) =>
          Math.min(index < 0 ? 0 : index + 1, rows.length - 1),
        )
      }
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      if (open && rows.length) {
        setActiveIndex((index) =>
          index < 0 ? rows.length - 1 : Math.max(index - 1, 0),
        )
      }
    } else if (event.key === 'Enter' && open && rows[activeIndex]) {
      event.preventDefault()
      choose(rows[activeIndex])
    } else if (event.key === 'Escape' && open) {
      event.preventDefault()
      setOpen(false)
      setQuery('')
      setActiveIndex(-1)
      triggerRef.current?.focus()
    } else if (event.key === 'PageDown' && open && next) {
      event.preventDefault()
      void loadMore()
    }
  }

  const activeOptionId =
    open && rows[activeIndex]
      ? `${listboxId}-${rows[activeIndex]?.id}`
      : undefined

  return (
    <div
      className="form-group remote-select"
      ref={rootRef}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) {
          setOpen(false)
          setQuery('')
          setActiveIndex(-1)
        }
      }}
    >
      <label className="form-label" htmlFor={id}>
        {label}
      </label>
      <button
        ref={triggerRef}
        type="button"
        id={id}
        className="form-input remote-select__input"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={open ? listboxId : undefined}
        disabled={!endpoint}
        onClick={() => {
          setQuery('')
          setOpen(!open)
        }}
        onKeyDown={handleKeyDown}
      >
        <span>
          {value
            ? choiceLabel(value)
            : !endpoint
              ? 'Selecciona primero la opción anterior'
              : 'Selecciona una opción'}
        </span>
        <ChevronDown size={18} aria-hidden="true" />
      </button>
      {open && endpoint && (
        <div className="remote-select__dropdown">
          <input
            ref={searchRef}
            className="form-input remote-select__search"
            role="combobox"
            aria-label={`Buscar ${label.toLowerCase()}`}
            aria-autocomplete="list"
            aria-expanded={open}
            aria-controls={listboxId}
            aria-activedescendant={activeOptionId}
            autoComplete="off"
            placeholder="Escribe para buscar…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={handleKeyDown}
          />
          {busy && rows.length === 0 && (
            <div
              className="remote-select__message"
              role="status"
              aria-live="polite"
            >
              Cargando opciones…
            </div>
          )}
          {!busy && !error && rows.length === 0 && (
            <div
              className="remote-select__message"
              role="status"
              aria-live="polite"
            >
              No hay opciones disponibles.
            </div>
          )}
          <div
            id={listboxId}
            className="remote-select__options"
            role="listbox"
            aria-label={label}
            aria-busy={busy}
          >
            {rows.map((row, index) => (
              <div
                id={`${listboxId}-${row.id}`}
                key={row.id}
                className={`remote-select__option${index === activeIndex ? ' remote-select__option--active' : ''}`}
                role="option"
                aria-selected={value?.id === row.id}
                onMouseDown={(event) => event.preventDefault()}
                onMouseEnter={() => setActiveIndex(index)}
                onClick={() => choose(row)}
              >
                {choiceLabel(row)}
              </div>
            ))}
          </div>
          {value && (
            <button
              type="button"
              className="remote-select__more"
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => choose(null)}
            >
              Limpiar selección
            </button>
          )}
          {error && (
            <div
              className="remote-select__message remote-select__message--error"
              role="alert"
            >
              {error}
              <button
                type="button"
                className="remote-select__more"
                onClick={() =>
                  next ? void loadMore() : setRetry((n) => n + 1)
                }
              >
                Reintentar
              </button>
            </div>
          )}
          {next && (
            <button
              type="button"
              className="remote-select__more"
              disabled={busy}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => void loadMore()}
            >
              {busy ? 'Cargando…' : 'Cargar más opciones'}
            </button>
          )}
        </div>
      )}
    </div>
  )
}
