import {
  useEffect,
  useId,
  useRef,
  useState,
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
} from 'react'
import { Eye, EyeOff, LoaderCircle, X } from 'lucide-react'

export function Button({
  variant = 'primary',
  className = '',
  busy,
  children,
  disabled,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'danger'
  busy?: boolean
}) {
  return (
    <button
      {...props}
      disabled={disabled || busy}
      aria-busy={busy}
      className={`btn btn--${variant} ${className}`}
    >
      {busy && (
        <LoaderCircle className="spinner" size={18} aria-hidden="true" />
      )}
      {children}
    </button>
  )
}

export function Field({
  label,
  hint,
  error,
  id: providedId,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & {
  label: string
  hint?: string
  error?: string
}) {
  const generatedId = useId()
  const id = providedId ?? generatedId
  return (
    <div className="form-group">
      <label className="form-label" htmlFor={id}>
        {label}
      </label>
      <input
        {...props}
        id={id}
        className={`form-input ${props.className ?? ''}`}
        aria-invalid={Boolean(error)}
        aria-describedby={error || hint ? `${id}-help` : undefined}
      />
      {(error || hint) && (
        <span id={`${id}-help`} className={error ? 'form-error' : 'form-hint'}>
          {error || hint}
        </span>
      )}
    </div>
  )
}

export function PasswordField({
  label,
  hint,
  id: providedId,
  ...props
}: Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> & {
  label: string
  hint?: string
}) {
  const generatedId = useId()
  const id = providedId ?? generatedId
  const [visible, setVisible] = useState(false)
  return (
    <div className="form-group">
      <label className="form-label" htmlFor={id}>
        {label}
      </label>
      <div className="password-wrapper">
        <input
          {...props}
          id={id}
          type={visible ? 'text' : 'password'}
          className="form-input"
          aria-describedby={hint ? `${id}-hint` : undefined}
        />
        <button
          type="button"
          className="password-toggle"
          aria-label={`${visible ? 'Ocultar' : 'Mostrar'} ${label.toLowerCase()}`}
          aria-pressed={visible}
          onClick={() => setVisible(!visible)}
        >
          {visible ? <EyeOff size={18} /> : <Eye size={18} />}
        </button>
      </div>
      {hint && (
        <span id={`${id}-hint`} className="form-hint">
          {hint}
        </span>
      )}
    </div>
  )
}

export function Feedback({
  children,
  variant = 'error',
}: {
  children: ReactNode
  variant?: 'error' | 'success' | 'info'
}) {
  return (
    <div
      className={`alert alert--${variant}`}
      role={variant === 'error' ? 'alert' : 'status'}
    >
      {children}
    </div>
  )
}

export function Loading({ children = 'Cargando…' }: { children?: ReactNode }) {
  return (
    <div className="loading-state" role="status">
      <LoaderCircle className="spinner" size={20} aria-hidden="true" />
      {children}
    </div>
  )
}

export function EmptyState({
  title,
  children,
}: {
  title: string
  children?: ReactNode
}) {
  return (
    <div className="empty-state" role="status">
      <strong>{title}</strong>
      {children}
    </div>
  )
}

export function AuthLayout({
  title,
  eyebrow,
  description,
  children,
  icon,
}: {
  title: string
  eyebrow?: string
  description?: string
  children: ReactNode
  icon?: ReactNode
}) {
  return (
    <main className="auth-page">
      <section className="card auth-card">
        {icon && <div className="auth-icon">{icon}</div>}
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1>{title}</h1>
        {description && <p>{description}</p>}
        {children}
      </section>
    </main>
  )
}

/** Native modal contains focus and returns it to its invoking control. */
export function Dialog({
  title,
  children,
  onClose,
  closeDisabled = false,
}: {
  title: string
  children: ReactNode
  onClose: () => void
  closeDisabled?: boolean
}) {
  const ref = useRef<HTMLDialogElement>(null)
  const titleId = useId()
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null
    const dialog = ref.current!
    dialog.showModal()
    return () => {
      dialog.close()
      previous?.focus()
    }
  }, [])
  return (
    <dialog
      className="dialog"
      ref={ref}
      aria-labelledby={titleId}
      onKeyDown={(event) => {
        if (event.key !== 'Tab') return
        const controls = Array.from(
          event.currentTarget.querySelectorAll<HTMLElement>(
            'button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex="0"]',
          ),
        ).filter((node) => node.getClientRects().length > 0)
        const first = controls[0]
        const last = controls[controls.length - 1]
        if (!first) {
          event.preventDefault()
          event.currentTarget.focus()
        } else if (event.shiftKey && document.activeElement === first) {
          event.preventDefault()
          last.focus()
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault()
          first.focus()
        }
      }}
      onCancel={(event) => {
        event.preventDefault()
        if (!closeDisabled) onClose()
      }}
    >
      <div className="section-header">
        <h2 id={titleId}>{title}</h2>
        <button
          autoFocus
          disabled={closeDisabled}
          type="button"
          className="icon-button"
          aria-label="Cerrar diálogo"
          onClick={onClose}
        >
          <X size={20} />
        </button>
      </div>
      {children}
    </dialog>
  )
}
