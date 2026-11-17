"""Persistencia en SQLite: velas, decisiones, órdenes, patrimonio, errores y estado de la cartera.

La restricción UNIQUE(simbolo, fecha_vela) en `decisiones` evita duplicar una operación
si llega dos veces la misma vela o si el backend se reinicia a mitad de un ciclo.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

ESQUEMA = """
CREATE TABLE IF NOT EXISTS velas (
  simbolo TEXT, fecha TEXT, open REAL, high REAL, low REAL, close REAL, volumen REAL,
  PRIMARY KEY (simbolo, fecha));
CREATE TABLE IF NOT EXISTS decisiones (
  id INTEGER PRIMARY KEY AUTOINCREMENT, simbolo TEXT NOT NULL, fecha_vela TEXT NOT NULL, creado TEXT NOT NULL,
  pronostico REAL, variables TEXT, respuesta_llm TEXT, latencia_s REAL, modelo_llm TEXT,
  accion_propuesta TEXT, justificacion TEXT, accion_final TEXT, aprobada INTEGER, motivo TEXT,
  UNIQUE (simbolo, fecha_vela));
CREATE TABLE IF NOT EXISTS ordenes (
  id INTEGER PRIMARY KEY AUTOINCREMENT, decision_id INTEGER REFERENCES decisiones(id), creado TEXT,
  accion TEXT, precio REAL, cantidad REAL, costo REAL, modo TEXT DEFAULT 'PAPER');
CREATE TABLE IF NOT EXISTS patrimonio (
  id INTEGER PRIMARY KEY AUTOINCREMENT, creado TEXT, fecha_vela TEXT, efectivo REAL, cantidad REAL,
  precio REAL, patrimonio REAL);
CREATE TABLE IF NOT EXISTS errores (
  id INTEGER PRIMARY KEY AUTOINCREMENT, creado TEXT, etapa TEXT, tipo TEXT, mensaje TEXT);
CREATE TABLE IF NOT EXISTS estado (clave TEXT PRIMARY KEY, valor TEXT);
"""


def ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class BD:
    def __init__(self, ruta: str):
        if ruta != ":memory:":
            Path(ruta).parent.mkdir(parents=True, exist_ok=True)
        self._con = sqlite3.connect(ruta, check_same_thread=False)
        self._con.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._con.executescript(ESQUEMA)

    def _ex(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self._lock, self._con:
            return self._con.execute(sql, params)

    def _todos(self, sql: str, params: tuple = ()) -> list[dict]:
        with self._lock:
            return [dict(r) for r in self._con.execute(sql, params).fetchall()]

    # --- escritura ---
    def guardar_velas(self, simbolo: str, velas) -> None:
        with self._lock, self._con:
            self._con.executemany("INSERT OR REPLACE INTO velas VALUES (?,?,?,?,?,?,?)",
                                  [(simbolo, v.fecha, v.open, v.high, v.low, v.close, v.volumen) for v in velas])

    def existe_decision(self, simbolo: str, fecha_vela: str) -> bool:
        return bool(self._todos("SELECT 1 FROM decisiones WHERE simbolo=? AND fecha_vela=?", (simbolo, fecha_vela)))

    def guardar_decision(self, d: dict) -> int | None:
        """Devuelve el id, o None si ya existía una decisión para esa vela (evento duplicado)."""
        cols = ["simbolo", "fecha_vela", "creado", "pronostico", "variables", "respuesta_llm", "latencia_s",
                "modelo_llm", "accion_propuesta", "justificacion", "accion_final", "aprobada", "motivo"]
        d = {**d, "creado": ahora(), "variables": json.dumps(d.get("variables", {}))}
        try:
            cur = self._ex(f"INSERT INTO decisiones ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                           tuple(d.get(c) for c in cols))
        except sqlite3.IntegrityError:
            return None
        return cur.lastrowid

    def guardar_orden(self, decision_id: int, accion: str, precio: float, cantidad: float, costo: float) -> None:
        self._ex("INSERT INTO ordenes (decision_id, creado, accion, precio, cantidad, costo) VALUES (?,?,?,?,?,?)",
                 (decision_id, ahora(), accion, precio, cantidad, costo))

    def guardar_patrimonio(self, fecha_vela: str, efectivo: float, cantidad: float, precio: float) -> None:
        self._ex("INSERT INTO patrimonio (creado, fecha_vela, efectivo, cantidad, precio, patrimonio) VALUES (?,?,?,?,?,?)",
                 (ahora(), fecha_vela, efectivo, cantidad, precio, efectivo + cantidad * precio))

    def error(self, etapa: str, exc: BaseException | str) -> None:
        tipo = type(exc).__name__ if isinstance(exc, BaseException) else "Aviso"
        self._ex("INSERT INTO errores (creado, etapa, tipo, mensaje) VALUES (?,?,?,?)",
                 (ahora(), etapa, tipo, str(exc)[:500]))

    def guardar_estado(self, clave: str, valor: dict) -> None:
        self._ex("INSERT OR REPLACE INTO estado VALUES (?,?)", (clave, json.dumps(valor)))

    # --- lectura ---
    def leer_estado(self, clave: str) -> dict | None:
        r = self._todos("SELECT valor FROM estado WHERE clave=?", (clave,))
        return json.loads(r[0]["valor"]) if r else None

    def decisiones(self, n: int = 30) -> list[dict]:
        return self._todos("SELECT * FROM decisiones ORDER BY id DESC LIMIT ?", (n,))

    def ordenes(self, n: int = 30) -> list[dict]:
        return self._todos("SELECT * FROM ordenes ORDER BY id DESC LIMIT ?", (n,))

    def errores(self, n: int = 30) -> list[dict]:
        return self._todos("SELECT * FROM errores ORDER BY id DESC LIMIT ?", (n,))

    def curva_patrimonio(self, n: int = 365) -> list[dict]:
        return self._todos("SELECT fecha_vela, patrimonio FROM patrimonio ORDER BY id DESC LIMIT ?", (n,))[::-1]
