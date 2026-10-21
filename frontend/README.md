# Frontend — Aerolínea Web

Aplicación web desarrollada con **React 18**, **TypeScript** y **Vite**, que implementa la consola de administración de vuelos para los casos de uso:
* **CU-01 (HU-001):** Programación de vuelos nacionales e internacionales con cálculo en tiempo real de duraciones, llegada local y distribución de sillas.
* **CU-02 (HU-002):** Edición y reprogramación de vuelos programados (fecha, hora y tarifas base) conservando código y ruta inmutables.
* **CU-03 (HU-003):** Cancelación de vuelos programados con registro de motivo, alternativas para pasajeros afectados y trazabilidad.

## Ejecución en Desarrollo

1. Asegúrate de que el backend esté corriendo en `http://localhost:8000`:
   ```bash
   docker compose up -d
   ```

2. Instala dependencias e inicia el servidor de desarrollo de Vite:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. Abre en tu navegador [http://localhost:5173/](http://localhost:5173/).

Vite incluye un proxy configurado hacia `http://127.0.0.1:8000` para las peticiones `/api/*`, garantizando la inclusión de cookies de sesión `HttpOnly` y protección CSRF.

## Compilación para Producción

```bash
cd frontend
npm run build
```
Genera los archivos estáticos optimizados en `frontend/dist/`.
