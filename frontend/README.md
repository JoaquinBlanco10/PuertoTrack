# PuertoTrack Frontend

Interfaz web de PuertoTrack con autenticación, rutas protegidas, panel principal y módulos operativos de contenedores y movimientos.

## Módulos disponibles

- **Dashboard:** indicadores de situación y coherencia, actividad de los últimos siete días y movimientos recientes para ambos roles.
- **Contenedores:** listado paginado por situación, búsqueda por código, detalle, alta controlada, corrección de código y regularización histórica. Las escrituras requieren rol `supervisor`.
- **Movimientos:** registro de entradas, traslados y salidas con destinos del catálogo, e historial global o por contenedor. Disponible para `operador` y `supervisor`.
- **Ubicaciones:** consulta del catálogo para ambos roles y administración (crear, editar o desactivar) para `supervisor`. No existe borrado físico.
- **Auditoría:** consulta paginada, filtros y comparación de valores anteriores y nuevos. Disponible exclusivamente para `supervisor`.

La ubicación y el estado de un contenedor no se editan desde el módulo de contenedores; cambian únicamente al registrar movimientos validados por el backend. La regularización histórica exige como evidencia un movimiento o una regularización previa auditada, corrige ubicación y estado de forma coherente y requiere una justificación. No crea ni modifica movimientos.

## Configuración local

1. Copia `.env.example` como `.env.local`.
2. Mantén `VITE_API_URL=http://localhost:8000` si FastAPI usa su puerto habitual.
3. Instala dependencias con `npm install`.
4. Inicia el frontend con `npm run dev`.

El backend debe permitir como `FRONTEND_ORIGIN` el origen mostrado por Vite. El valor predeterminado es `http://localhost:5173`.

## Sesión

El JWT se conserva exclusivamente en el estado en memoria de React. No se escribe en `localStorage`, `sessionStorage` ni cookies. Por diseño, recargar o cerrar la pestaña termina la sesión del prototipo.

El Dashboard interpreta su período como siete días calendario UTC. Las fechas del gráfico y los horarios de movimientos recientes se muestran explícitamente en UTC para evitar desplazamientos según la zona horaria del navegador.

## Comandos

- `npm run dev`: servidor de desarrollo.
- `npm run typecheck`: validación de TypeScript.
- `npm test`: pruebas unitarias del cliente HTTP.
- `npm run build`: compilación de producción.
