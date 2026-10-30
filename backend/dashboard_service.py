from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy.orm import Session

from repositories import DashboardRepository
from schemas import (
    DashboardResumenRespuesta,
    MovimientoDiarioDashboard,
    PeriodoDashboard,
    TotalesContenedoresDashboard,
)


ZONA_HORARIA_DASHBOARD = "UTC"
DIAS_DASHBOARD = 7


class DashboardService:
    def __init__(self, session: Session) -> None:
        self.repository = DashboardRepository(session)

    def obtener_resumen(
        self, ahora: datetime | None = None
    ) -> DashboardResumenRespuesta:
        instante = ahora or datetime.now(timezone.utc)
        if instante.tzinfo is None:
            instante = instante.replace(tzinfo=timezone.utc)
        instante_utc = instante.astimezone(timezone.utc)

        fecha_hasta = instante_utc.date()
        fecha_desde = fecha_hasta - timedelta(days=DIAS_DASHBOARD - 1)
        desde = datetime.combine(fecha_desde, time.min, tzinfo=timezone.utc)
        hasta_exclusivo = datetime.combine(
            fecha_hasta + timedelta(days=1),
            time.min,
            tzinfo=timezone.utc,
        )

        movimientos_por_fecha = {
            fecha_desde + timedelta(days=desplazamiento): {
                "entrada": 0,
                "traslado": 0,
                "salida": 0,
            }
            for desplazamiento in range(DIAS_DASHBOARD)
        }
        for dia, tipo, cantidad in self.repository.agrupar_movimientos_por_dia(
            desde=desde,
            hasta_exclusivo=hasta_exclusivo,
        ):
            fecha = dia if isinstance(dia, date) else date.fromisoformat(str(dia))
            if fecha in movimientos_por_fecha:
                movimientos_por_fecha[fecha][tipo] = cantidad

        serie = [
            MovimientoDiarioDashboard(
                fecha=fecha,
                entrada=cantidades["entrada"],
                traslado=cantidades["traslado"],
                salida=cantidades["salida"],
            )
            for fecha, cantidades in movimientos_por_fecha.items()
        ]

        return DashboardResumenRespuesta(
            generado_en=instante_utc,
            zona_horaria=ZONA_HORARIA_DASHBOARD,
            periodo=PeriodoDashboard(
                desde=fecha_desde,
                hasta=fecha_hasta,
                dias=DIAS_DASHBOARD,
            ),
            contenedores=TotalesContenedoresDashboard(
                **self.repository.contar_contenedores()
            ),
            movimientos_ultimos_7_dias=serie,
            ultimos_movimientos=self.repository.ultimos_movimientos(limite=10),
        )
