// Cliente de la API del bot. La clave se escribe en la interfaz y se guarda solo en esta
// pestaña (sessionStorage); nunca va en el código ni en variables de Vite.

export interface Cartera { efectivo: number; cantidad: number; precio_entrada: number; posicion: number; dia: string }
export interface Ultimo {
  creado: string; fecha_vela: string; precio_ejecucion: number
  contexto: { pronostico: number; dist_sma20: number; vol20: number; rend_ultimo: number; cierre: number }
  propuesta: string | null; justificacion: string | null; latencia_s: number | null
  accion_final: string; aprobada: boolean; motivo: string
}
export interface Estado {
  version: string; modo: string; estado: 'DETENIDO' | 'CORRIENDO' | 'PAUSADO'; simbolo: string; intervalo: string
  modelo: { nombre: string; cargado: boolean; meta: Record<string, unknown> }
  llm: { modelo: string; local: boolean }
  cartera: Cartera; patrimonio: number; capital_inicial: number
  riesgo: { exposicion_max: number; perdida_diaria_max: number; antiguedad_max_h: number; costo: number; deslizamiento: number }
  ultimo: Ultimo | null
}
export interface Decision {
  id: number; fecha_vela: string; creado: string; pronostico: number; accion_propuesta: string | null
  justificacion: string | null; accion_final: string; aprobada: number; motivo: string; latencia_s: number | null
}
export interface ErrorBot { id: number; creado: string; etapa: string; tipo: string; mensaje: string }

const CLAVE = 'bot_api_key'

export function leerClave(): string {
  try { return sessionStorage.getItem(CLAVE) ?? '' } catch { return '' }
}
export function guardarClave(v: string): void {
  try { sessionStorage.setItem(CLAVE, v) } catch { /* sin almacenamiento: se usa solo en memoria */ }
}

export class ApiError extends Error {
  constructor(public status: number, mensaje: string) { super(mensaje) }
}

async function pedir<T>(ruta: string, clave: string, metodo = 'GET'): Promise<T> {
  let r: Response
  try {
    r = await fetch(`/api${ruta}`, { method: metodo, headers: { 'X-API-Key': clave } })
  } catch {
    throw new ApiError(0, 'El backend no responde en 127.0.0.1:8000')
  }
  if (!r.ok) {
    const cuerpo = await r.json().catch(() => ({}))
    throw new ApiError(r.status, cuerpo.detail ?? `Error ${r.status}`)
  }
  return r.json() as Promise<T>
}

export const api = {
  estado: (k: string) => pedir<Estado>('/estado', k),
  decisiones: (k: string) => pedir<Decision[]>('/decisiones?n=20', k),
  errores: (k: string) => pedir<ErrorBot[]>('/errores?n=10', k),
  control: (k: string, accion: 'iniciar' | 'pausar' | 'detener') => pedir<{ estado: string }>(`/control/${accion}`, k, 'POST'),
  ciclo: (k: string) => pedir<Record<string, unknown>>('/ciclo', k, 'POST'),
}
