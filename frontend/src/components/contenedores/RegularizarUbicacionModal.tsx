import { type FormEvent, useEffect, useState } from "react";

import { mensajeErrorApi } from "../../lib/errores";
import type {
  Contenedor,
  RegularizarContenedorInput,
  Ubicacion,
} from "../../types/logistica";
import { UbicacionCombobox } from "../ubicaciones/UbicacionCombobox";
import { Alerta } from "../ui/Feedback";
import { Modal } from "../ui/Modal";

interface Props {
  abierto: boolean;
  contenedor: Contenedor | null;
  ubicaciones: Ubicacion[];
  onCerrar: () => void;
  onConfirmar: (
    contenedorId: number,
    datos: RegularizarContenedorInput,
  ) => Promise<void>;
}

export function RegularizarUbicacionModal({
  abierto,
  contenedor,
  ubicaciones,
  onCerrar,
  onConfirmar,
}: Props) {
  const [seleccionada, setSeleccionada] = useState<Ubicacion | null>(null);
  const [estado, setEstado] = useState<"en_patio" | "en_transito">("en_patio");
  const [justificacion, setJustificacion] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!abierto) return;
    setSeleccionada(null);
    setEstado("en_patio");
    setJustificacion("");
    setError(null);
  }, [abierto]);

  const seleccionar = (ubicacion: Ubicacion | null) => {
    setSeleccionada(ubicacion);
    if (ubicacion) {
      setEstado(ubicacion.tipo === "interna" ? "en_patio" : "en_transito");
    }
    setError(null);
  };

  const estadoEsperado = seleccionada?.tipo === "externa" ? "en_transito" : "en_patio";
  const coherente = !seleccionada || estado === estadoEsperado;

  const enviar = async (evento: FormEvent) => {
    evento.preventDefault();
    if (!contenedor || !seleccionada) return setError("Selecciona una ubicación validada.");
    if (!coherente) return setError("El estado elegido no corresponde al tipo de ubicación.");
    if (justificacion.trim().length < 10) return setError("La justificación debe tener al menos 10 caracteres.");
    setEnviando(true);
    setError(null);
    try {
      await onConfirmar(contenedor.id, {
        ubicacion_id: seleccionada.id,
        estado,
        justificacion: justificacion.trim(),
      });
    } catch (motivo) {
      setError(mensajeErrorApi(motivo, "No fue posible regularizar la información histórica."));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <Modal abierto={abierto} titulo="Regularizar información histórica" descripcion={`Corrige ubicación y estado de ${contenedor?.codigo ?? "este contenedor"} usando evidencia existente.`} onCerrar={onCerrar} bloqueado={enviando} ancho="amplio">
      <form onSubmit={enviar} className="space-y-5">
        <Alerta tipo="info">
          Esta corrección no registra un movimiento ni modifica el historial. Los valores anteriores, los nuevos, tu identidad y la justificación quedarán auditados.
        </Alerta>

        {contenedor && (
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Información actual</p>
              <p className="mt-2 text-sm font-bold text-ink-900">{contenedor.ubicacion_actual}</p>
              <p className="mt-1 text-xs text-slate-500">Estado: {contenedor.estado.replaceAll("_", " ")}</p>
            </div>
            <div className="rounded-2xl border border-harbor-100 bg-harbor-50/60 p-4">
              <p className="text-[10px] font-bold uppercase tracking-wider text-harbor-700">Corrección propuesta</p>
              <p className="mt-2 text-sm font-bold text-ink-900">{seleccionada?.nombre ?? "Selecciona una ubicación"}</p>
              <p className="mt-1 text-xs text-slate-500">Estado: {seleccionada ? estado.replaceAll("_", " ") : "pendiente"}</p>
            </div>
          </div>
        )}

        <UbicacionCombobox etiqueta="Ubicación histórica validada" ubicaciones={ubicaciones.filter((u) => u.activo)} seleccionada={seleccionada} onSeleccionar={seleccionar} autoFocus />

        <div>
          <label htmlFor="regularizacion-estado" className="mb-2 block text-sm font-bold text-slate-700">Estado operacional corregido</label>
          <select id="regularizacion-estado" value={estado} onChange={(evento) => setEstado(evento.target.value as "en_patio" | "en_transito")} disabled={!seleccionada} className={`h-12 w-full rounded-xl border bg-white px-4 text-sm outline-none focus:ring-4 ${coherente ? "border-slate-200 focus:border-harbor-500 focus:ring-harbor-100" : "border-rose-300 focus:ring-rose-100"}`}>
            <option value="en_patio">En patio</option>
            <option value="en_transito">En tránsito</option>
          </select>
          {seleccionada && <p className="mt-1.5 text-xs text-slate-400">Una ubicación {seleccionada.tipo} requiere el estado “{estadoEsperado.replaceAll("_", " ")}”.</p>}
        </div>

        <div>
          <label htmlFor="regularizacion-justificacion" className="mb-2 block text-sm font-bold text-slate-700">Justificación obligatoria</label>
          <textarea id="regularizacion-justificacion" value={justificacion} onChange={(evento) => setJustificacion(evento.target.value)} minLength={10} maxLength={500} required rows={4} placeholder="Indica el documento, manifiesto u otra evidencia histórica revisada" className="w-full resize-y rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-harbor-500 focus:ring-4 focus:ring-harbor-100" />
          <p className="mt-1.5 text-right text-xs text-slate-400">{justificacion.length}/500</p>
        </div>

        {!coherente && <Alerta tipo="error">La ubicación y el estado propuestos no son coherentes.</Alerta>}
        {error && <Alerta tipo="error">{error}</Alerta>}
        <div className="flex flex-col-reverse gap-3 border-t border-slate-100 pt-5 sm:flex-row sm:justify-end">
          <button type="button" onClick={onCerrar} disabled={enviando} className="rounded-xl border border-slate-200 px-5 py-3 text-sm font-bold text-slate-600">Cancelar</button>
          <button type="submit" disabled={!seleccionada || !coherente || justificacion.trim().length < 10 || enviando} className="rounded-xl bg-ink-900 px-5 py-3 text-sm font-bold text-white disabled:opacity-40">{enviando ? "Regularizando…" : "Confirmar corrección histórica"}</button>
        </div>
      </form>
    </Modal>
  );
}
