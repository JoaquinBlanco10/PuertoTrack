import { type FormEvent, useEffect, useState } from "react";

import { mensajeErrorApi } from "../../lib/errores";
import type { Contenedor, CrearContenedorInput } from "../../types/logistica";
import { Alerta } from "../ui/Feedback";
import { Modal } from "../ui/Modal";

interface ContenedorFormModalProps {
  abierto: boolean;
  contenedor?: Contenedor | null;
  onCerrar: () => void;
  onCrear: (datos: CrearContenedorInput) => Promise<void>;
  onCorregir: (contenedorId: number, codigo: string) => Promise<void>;
}

export function ContenedorFormModal({
  abierto,
  contenedor,
  onCerrar,
  onCrear,
  onCorregir,
}: ContenedorFormModalProps) {
  const editando = Boolean(contenedor);
  const [codigo, setCodigo] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!abierto) return;
    setCodigo(contenedor?.codigo ?? "");
    setError(null);
  }, [abierto, contenedor]);

  const enviar = async (evento: FormEvent<HTMLFormElement>) => {
    evento.preventDefault();
    setError(null);

    if (!codigo.trim()) {
      setError("El código es obligatorio.");
      return;
    }
    setEnviando(true);
    try {
      if (contenedor) {
        await onCorregir(contenedor.id, codigo.trim());
      } else {
        await onCrear({ codigo: codigo.trim() });
      }
    } catch (motivo) {
      setError(mensajeErrorApi(motivo));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <Modal
      abierto={abierto}
      titulo={editando ? "Corregir código" : "Nuevo contenedor"}
      descripcion={
        editando
          ? "Solo el código puede corregirse directamente."
          : "El alta comienza sin ubicación confirmada; la primera entrada se registra en Movimientos."
      }
      onCerrar={onCerrar}
      bloqueado={enviando}
    >
      <form onSubmit={enviar} className="space-y-5">
        <div>
          <label htmlFor="contenedor-codigo" className="mb-2 block text-sm font-bold text-slate-700">
            Código
          </label>
          <input
            id="contenedor-codigo"
            value={codigo}
            onChange={(evento) => setCodigo(evento.target.value.toUpperCase())}
            maxLength={20}
            required
            autoFocus
            placeholder="Ej. MSCU1234567"
            className="h-12 w-full rounded-xl border border-slate-200 px-4 font-mono text-sm font-bold uppercase tracking-wider text-ink-900 outline-none transition focus:border-harbor-500 focus:ring-4 focus:ring-harbor-100"
          />
          <p className="mt-1.5 text-xs text-slate-400">Máximo 20 caracteres; el backend normaliza a mayúsculas.</p>
        </div>

        {!editando && (
          <Alerta tipo="info">
            Se creará como “disponible”, con ubicación “Sin asignar” y presencia sin confirmar. La primera entrada debe realizarse desde Movimientos.
          </Alerta>
        )}

        {editando && (
          <Alerta tipo="info">
            La ubicación y el estado actuales se conservarán para proteger la trazabilidad.
          </Alerta>
        )}

        {error && <Alerta tipo="error">{error}</Alerta>}

        <div className="flex flex-col-reverse gap-3 border-t border-slate-100 pt-5 sm:flex-row sm:justify-end">
          <button
            type="button"
            onClick={onCerrar}
            disabled={enviando}
            className="rounded-xl border border-slate-200 px-5 py-3 text-sm font-bold text-slate-600 transition hover:bg-slate-50 disabled:opacity-50"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={enviando}
            className="rounded-xl bg-ink-900 px-5 py-3 text-sm font-bold text-white transition hover:bg-ink-700 focus:outline-none focus:ring-4 focus:ring-harbor-200 disabled:cursor-wait disabled:opacity-60"
          >
            {enviando ? "Guardando…" : editando ? "Confirmar corrección" : "Crear contenedor"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
