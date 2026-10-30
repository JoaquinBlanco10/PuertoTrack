import { type FormEvent, useEffect, useState } from "react";

import { mensajeErrorApi } from "../../lib/errores";
import type { CrearUbicacionInput, TipoUbicacion, Ubicacion } from "../../types/logistica";
import { Alerta } from "../ui/Feedback";
import { Modal } from "../ui/Modal";

interface Props {
  abierto: boolean;
  ubicacion: Ubicacion | null;
  onCerrar: () => void;
  onCrear: (datos: CrearUbicacionInput) => Promise<void>;
  onActualizar: (id: number, datos: { nombre: string; tipo: TipoUbicacion; activo: boolean }) => Promise<void>;
}

export function UbicacionFormModal({ abierto, ubicacion, onCerrar, onCrear, onActualizar }: Props) {
  const [codigo, setCodigo] = useState("");
  const [nombre, setNombre] = useState("");
  const [tipo, setTipo] = useState<TipoUbicacion>("interna");
  const [activo, setActivo] = useState(true);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!abierto) return;
    setCodigo(ubicacion?.codigo ?? "");
    setNombre(ubicacion?.nombre ?? "");
    setTipo(ubicacion?.tipo ?? "interna");
    setActivo(ubicacion?.activo ?? true);
    setError(null);
  }, [abierto, ubicacion]);

  const enviar = async (evento: FormEvent) => {
    evento.preventDefault();
    if (!codigo.trim() || !nombre.trim()) return setError("Código y nombre son obligatorios.");
    setEnviando(true);
    setError(null);
    try {
      if (ubicacion) await onActualizar(ubicacion.id, { nombre: nombre.trim(), tipo, activo });
      else await onCrear({ codigo: codigo.trim(), nombre: nombre.trim(), tipo });
    } catch (motivo) {
      setError(mensajeErrorApi(motivo, "No fue posible guardar la ubicación."));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <Modal abierto={abierto} titulo={ubicacion ? "Editar ubicación" : "Nueva ubicación"} descripcion="El código es único y estable. El tipo queda bloqueado después del primer uso." onCerrar={onCerrar} bloqueado={enviando}>
      <form onSubmit={enviar} className="space-y-5">
        <div>
          <label htmlFor="ubicacion-codigo" className="mb-2 block text-sm font-bold text-slate-700">Código</label>
          <input id="ubicacion-codigo" value={codigo} onChange={(e) => setCodigo(e.target.value.toUpperCase())} disabled={Boolean(ubicacion)} required maxLength={30} autoFocus className="h-12 w-full rounded-xl border border-slate-200 px-4 font-mono text-sm font-bold outline-none focus:border-harbor-500 focus:ring-4 focus:ring-harbor-100 disabled:bg-slate-100" placeholder="PATIO_NORTE" />
        </div>
        <div>
          <label htmlFor="ubicacion-nombre" className="mb-2 block text-sm font-bold text-slate-700">Nombre visible</label>
          <input id="ubicacion-nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} required maxLength={120} className="h-12 w-full rounded-xl border border-slate-200 px-4 text-sm outline-none focus:border-harbor-500 focus:ring-4 focus:ring-harbor-100" placeholder="Patio Norte" />
        </div>
        <div>
          <label htmlFor="ubicacion-tipo" className="mb-2 block text-sm font-bold text-slate-700">Tipo</label>
          <select id="ubicacion-tipo" value={tipo} onChange={(e) => setTipo(e.target.value as TipoUbicacion)} className="h-12 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm outline-none focus:border-harbor-500 focus:ring-4 focus:ring-harbor-100">
            <option value="interna">Interna</option><option value="externa">Externa</option>
          </select>
        </div>
        {ubicacion && (
          <label className="flex items-center justify-between rounded-xl border border-slate-200 p-4">
            <span><span className="block text-sm font-bold text-slate-700">Ubicación habilitada</span><span className="mt-1 block text-xs text-slate-400">Las ubicaciones inactivas no aparecen como destinos.</span></span>
            <input type="checkbox" checked={activo} onChange={(e) => setActivo(e.target.checked)} className="h-5 w-5 accent-harbor-600" />
          </label>
        )}
        {error && <Alerta tipo="error">{error}</Alerta>}
        <div className="flex flex-col-reverse gap-3 border-t border-slate-100 pt-5 sm:flex-row sm:justify-end">
          <button type="button" onClick={onCerrar} disabled={enviando} className="rounded-xl border border-slate-200 px-5 py-3 text-sm font-bold text-slate-600">Cancelar</button>
          <button type="submit" disabled={enviando} className="rounded-xl bg-ink-900 px-5 py-3 text-sm font-bold text-white disabled:opacity-50">{enviando ? "Guardando…" : "Guardar ubicación"}</button>
        </div>
      </form>
    </Modal>
  );
}
