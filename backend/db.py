#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
db.py – Módulo de persistência SQLite para o Sistema de IPTU
=============================================================
Gerencia:
  • Sessões de geração (histórico)
  • Linhas de log de cada sessão
  • Arquivos PDF produzidos por sessão
  • Operações de exclusão

Banco criado automaticamente em: <pasta_do_app>/logs/iptu.db
"""

import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

# ── Localização do banco ──────────────────────────────────────────────────────
_DB_PATH: Path | None = None
_lock = threading.Lock()


def inicializar(app_dir: Path | str):
    """
    Chama uma vez ao iniciar o app.
    Cria a pasta logs/ e o banco iptu.db se não existirem.
    """
    global _DB_PATH
    logs_dir = Path(app_dir) / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    _DB_PATH = logs_dir / "iptu.db"
    _criar_tabelas()
    print(f"[DB] Banco de dados: {_DB_PATH}")


def _db_path() -> Path:
    if _DB_PATH is None:
        raise RuntimeError("db.inicializar() não foi chamado.")
    return _DB_PATH


@contextmanager
def _conn():
    """Context manager com conexão thread-safe."""
    with _lock:
        con = sqlite3.connect(str(_db_path()), timeout=10,
                              detect_types=sqlite3.PARSE_DECLTYPES)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA foreign_keys=ON")
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()


def _criar_tabelas():
    with _conn() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS sessoes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            iniciado_em TEXT    NOT NULL,
            finalizado_em TEXT,
            status      TEXT    NOT NULL DEFAULT 'em_andamento',
                                          -- em_andamento | concluido | cancelado | erro
            arquivos_entrada TEXT,        -- nomes dos TXTs (separados por vírgula)
            total_registros  INTEGER DEFAULT 0,
            total_paginas    INTEGER DEFAULT 0,
            num_pdfs         INTEGER DEFAULT 0,
            pasta_saida      TEXT,
            erro_msg         TEXT
        );

        CREATE TABLE IF NOT EXISTS logs (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            sessao_id  INTEGER NOT NULL REFERENCES sessoes(id) ON DELETE CASCADE,
            momento    TEXT    NOT NULL,
            tipo       TEXT    NOT NULL DEFAULT 'info',  -- info | ok | warn | err
            mensagem   TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS pdfs_gerados (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            sessao_id  INTEGER NOT NULL REFERENCES sessoes(id) ON DELETE CASCADE,
            nome       TEXT    NOT NULL,
            caminho    TEXT    NOT NULL,
            tamanho_mb REAL,
            criado_em  TEXT    NOT NULL,
            excluido   INTEGER NOT NULL DEFAULT 0,
            excluido_em TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_logs_sessao    ON logs(sessao_id);
        CREATE INDEX IF NOT EXISTS idx_pdfs_sessao    ON pdfs_gerados(sessao_id);
        CREATE INDEX IF NOT EXISTS idx_sessoes_status ON sessoes(status);
        """)


# ── API pública ───────────────────────────────────────────────────────────────

def abrir_sessao(arquivos_entrada: list[str]) -> int:
    """Cria uma nova sessão e retorna seu ID."""
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO sessoes (iniciado_em, arquivos_entrada) VALUES (?, ?)",
            (_now(), ", ".join(arquivos_entrada))
        )
        return cur.lastrowid


def fechar_sessao(sessao_id: int, status: str, total_registros=0,
                  total_paginas=0, num_pdfs=0, pasta_saida="", erro_msg=""):
    with _conn() as con:
        con.execute("""
            UPDATE sessoes SET
                finalizado_em   = ?,
                status          = ?,
                total_registros = ?,
                total_paginas   = ?,
                num_pdfs        = ?,
                pasta_saida     = ?,
                erro_msg        = ?
            WHERE id = ?
        """, (_now(), status, total_registros, total_paginas,
              num_pdfs, pasta_saida, erro_msg, sessao_id))


def registrar_log(sessao_id: int, mensagem: str, tipo: str = "info"):
    with _conn() as con:
        con.execute(
            "INSERT INTO logs (sessao_id, momento, tipo, mensagem) VALUES (?, ?, ?, ?)",
            (sessao_id, _now(), tipo, mensagem)
        )


def registrar_pdf(sessao_id: int, caminho: str, tamanho_mb: float):
    from pathlib import Path as _Path
    nome = _Path(caminho).name
    with _conn() as con:
        con.execute("""
            INSERT INTO pdfs_gerados (sessao_id, nome, caminho, tamanho_mb, criado_em)
            VALUES (?, ?, ?, ?, ?)
        """, (sessao_id, nome, caminho, tamanho_mb, _now()))


def marcar_pdf_excluido(caminho: str):
    with _conn() as con:
        con.execute("""
            UPDATE pdfs_gerados SET excluido = 1, excluido_em = ?
            WHERE caminho = ?
        """, (_now(), caminho))


def listar_sessoes(limite: int = 50) -> list[dict]:
    with _conn() as con:
        rows = con.execute("""
            SELECT s.*,
                   COUNT(DISTINCT p.id)                           AS total_pdfs_db,
                   SUM(CASE WHEN p.excluido=0 THEN 1 ELSE 0 END) AS pdfs_ativos
            FROM sessoes s
            LEFT JOIN pdfs_gerados p ON p.sessao_id = s.id
            GROUP BY s.id
            ORDER BY s.id DESC
            LIMIT ?
        """, (limite,)).fetchall()
        return [dict(r) for r in rows]


def detalhe_sessao(sessao_id: int) -> dict | None:
    with _conn() as con:
        row = con.execute("SELECT * FROM sessoes WHERE id=?", (sessao_id,)).fetchone()
        if not row:
            return None
        sessao = dict(row)

        sessao["logs"] = [dict(r) for r in con.execute(
            "SELECT momento, tipo, mensagem FROM logs WHERE sessao_id=? ORDER BY id",
            (sessao_id,)
        ).fetchall()]

        sessao["pdfs"] = [dict(r) for r in con.execute(
            "SELECT nome, caminho, tamanho_mb, criado_em, excluido, excluido_em "
            "FROM pdfs_gerados WHERE sessao_id=? ORDER BY id",
            (sessao_id,)
        ).fetchall()]

        return sessao


def estatisticas() -> dict:
    with _conn() as con:
        r = con.execute("""
            SELECT
                COUNT(*)                                              AS total_sessoes,
                SUM(CASE WHEN status='concluido'  THEN 1 ELSE 0 END) AS concluidas,
                SUM(CASE WHEN status='cancelado'  THEN 1 ELSE 0 END) AS canceladas,
                SUM(CASE WHEN status='erro'       THEN 1 ELSE 0 END) AS com_erro,
                COALESCE(SUM(total_registros), 0)                     AS total_registros,
                COALESCE(SUM(total_paginas),   0)                     AS total_paginas,
                COALESCE(SUM(num_pdfs),        0)                     AS total_pdfs
            FROM sessoes
        """).fetchone()
        return dict(r)


def fechar_sessoes_orfas():
    """
    Chamado ao iniciar o app. Marca como 'erro' qualquer sessão que tenha
    ficado com status 'em_andamento' de uma execução anterior (crash, kill, etc).
    """
    with _conn() as con:
        con.execute("""
            UPDATE sessoes
            SET status = 'erro',
                finalizado_em = ?,
                erro_msg = 'Sessão interrompida — o sistema foi encerrado durante o processamento.'
            WHERE status = 'em_andamento'
        """, (_now(),))


def _now() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

def excluir_sessao(sessao_id: int):
    """Remove uma sessão e seus logs/pdfs em cascata."""
    with _conn() as con:
        con.execute("DELETE FROM sessoes WHERE id = ?", (sessao_id,))


def limpar_historico_completo():
    """Remove todas as sessões, logs e registros de PDFs."""
    with _conn() as con:
        con.executescript("""
            DELETE FROM logs;
            DELETE FROM pdfs_gerados;
            DELETE FROM sessoes;
        """)
