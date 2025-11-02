# Mortalidad Colombia 2019

Aplicación Dash para explorar estadísticas de mortalidad en Colombia durante 2019. El proyecto sigue prácticas de ingeniería de plataforma con tipado estricto, automatización y despliegue reproducible.

## Requisitos

- Python 3.11+
- Make (GNU)
- Docker (opcional para despliegue contenedorizado)

## Cómo correr local

1. Copia `.env.example` a `.env` y ajusta rutas o puertos según tu entorno.
2. Coloca los archivos `NoFetal2019.xlsx`, `CodigosDeMuerte.xlsx` y `Divipola.xlsx` dentro de `data/raw/` (el repositorio ignora esta carpeta por defecto).
3. Ejecuta `make dev-install` para crear el entorno virtual, instalar dependencias y registrar la biblioteca como editable.
4. Inicia la aplicación con `make run` o `python -m mortalidad.app`. La interfaz estará disponible en `http://localhost:8050`.

## Cómo testear

- Ejecuta `make lint` para revisar estilo con Ruff.
- Corre `make typecheck` para validar tipado estático con MyPy.
- Lanza `make test` para correr pytest y generar el reporte de cobertura configurado.
- Si necesitas cobertura detallada, puedes repetir `pytest --cov=src --cov-report=term-missing`.

## Calidad de código

- `make format` aplica `isort` y `black` siguiendo la configuración en `pyproject.toml`.
- `make lint`, `make typecheck` y `make test` deben pasar antes de subir cambios.
- Registra los hooks ejecutando `make pre-commit`; esto habilita `ruff`, `black`, `isort`, `detect-secrets` y utilidades básicas antes de cada commit.

## CLI

- `python -m mortalidad.cli ingest` procesa los archivos XLSX y genera `data/processed/mortalidad_2019.parquet`.
- `python -m mortalidad.cli validate` ejecuta la validación con Pandera sobre el parquet procesado.
- `python -m mortalidad.cli serve --host 0.0.0.0 --port 8050` levanta la aplicación Dash usando la configuración actual.

## Accesibilidad y rendimiento

- Las gráficas se envuelven en `dcc.Loading` para diferir la renderización y mostrar progreso.
- Los filtros conservan caché (configurable vía `CACHE_TIMEOUT`) y el rango de meses se actualiza al soltar el control, reduciendo callbacks consecutivos.
- Cada tarjeta tiene un botón “Exportar CSV” que descarga la vista actual mediante `dcc.Download`.
- El layout usa roles y atributos `aria-*`, botones con alto contraste y estilos `:focus-visible` para navegación asistiva.

## Integración con PyCharm

- Importa el repositorio y selecciona el intérprete virtual (`.venv`) creado con `make dev-install`.
- Desde el menú **Run > Edit Configurations…**, usa la opción **Import from .run** para cargar:
  - `Dash Server` (ejecuta el servidor en modo debug con variables de entorno).
  - `PyTests` (lanza la suite de pytest con cobertura y warnings mínimos).
  - `CLI Ingest` (corre el comando `python -m mortalidad.cli ingest`).
- Ajusta las variables `DATA_DIR`, `ENV` o `PORT` desde el propio diálogo si tu entorno difiere de los valores por defecto del proyecto.
- El depurador de PyCharm puede engancharse a cualquiera de las configuraciones anteriores presionando el icono de bug junto a cada run configuration.

## Cómo desplegar

- Construye la imagen con `docker compose build` y levanta los contenedores mediante `make up`.
- Render: actualiza `render.yaml` y `Procfile` si cambias el módulo principal. Render detecta el comando `gunicorn mortalidad.app:server`.
- Railway o AWS ECS/Fargate: reutiliza el `Dockerfile` multi-stage y ajusta variables de entorno (`ENV`, `PORT`, `DATA_DIR`) desde el panel correspondiente. Asegúrate de montar o sincronizar los datos en `data/`.

## Estructura del proyecto

```
├── data/
│   ├── processed/
│   └── raw/
├── src/
│   └── mortalidad/
├── tests/
└── assets/
```

Documenta transformaciones de datos adicionales en `data/README.md` y conserva los scripts utilitarios en `src/mortalidad/utils/`.
