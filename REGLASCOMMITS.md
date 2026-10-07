# Reglas de trabajo

## Flujo de cada Historia de Usuario

```
git switch -c feat/HU-12-busqueda-vuelos
# ...trabajar...
git add .
git commit -m "feat(HU-12): agrega endpoint de búsqueda de vuelos"
git push -u origin feat/HU-12-busqueda-vuelos
```

Luego: abrir PR en GitHub → 1 aprobación → **Squash and merge** → borrar la rama.

## Ramas

`feat/HU-N-descripcion`

- Por cada Historia de Usuario se debe crear una rama, creada siempre desde `main`.

## Posibles tipos de commits

| Tipo    | Se usa para                  |
|---------|------------------------------|
| `feat`  | Funcionalidad nueva          |
| `fix`   | Corrección de un error       |
| `docs`  | Documentación                |
| `test`  | Pruebas                      |
| `chore` | Configuración y tareas menores |

Todo commit realizado debe caer dentro de unas de estas 5 categorias

## Pull Requests

- Un Pull Request = una Historia de Usuario.
- Necesita 1 aprobación minimo de otra persona del equipo.
- Se une a main con **Squash and merge** de Github.

## Nunca

- Subir directo a `main`.
- Usar `git push --force`.
- Subir `.env`, contraseñas o llaves.