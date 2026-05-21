#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IPTU Gerador – API FastAPI
Prefeitura Municipal de Santa Luzia / MG
"""

import os
import io as _io
import uuid
import shutil
import threading
import traceback
import zipfile
import re
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
import uvicorn

import db
from motor_iptu import processar_arquivo

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent
DATA_DIR   = BASE_DIR / "data"
PDFS_DIR   = DATA_DIR / "pdfs"
UPLOAD_DIR = DATA_DIR / "uploads"
LOGS_DIR   = DATA_DIR / "logs"

for d in [DATA_DIR, PDFS_DIR, UPLOAD_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

db.inicializar(DATA_DIR)
db.fechar_sessoes_orfas()

# ── Estado global de progresso ────────────────────────────────────────────────
_progress: dict = {}
_cancel_flags: dict = {}


app = FastAPI(title="IPTU Gerador API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/pdfs",   StaticFiles(directory=str(PDFS_DIR)),             name="pdfs")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _detectar_ano(caminho: Path) -> str:
    try:
        with open(caminho, "rb") as f:
            linha = f.readline()
            ano = linha[793:797].decode("latin-1", errors="replace").strip()
            if ano.isdigit():
                return ano
    except Exception:
        pass
    return datetime.now().strftime("%Y")

def _contar_registros(caminho: Path) -> int:
    """Conta registros não-vazios sem carregar tudo em memória."""
    total = 0
    with open(caminho, "rb") as f:
        for linha in f:
            if linha.strip():
                total += 1
    return total


# ── Worker de geração ─────────────────────────────────────────────────────────

def _worker_geracao(job_id: str, arquivos: list[Path], verso_path: Optional[Path]):
    cancel_ev = _cancel_flags.get(job_id)
    prog = _progress[job_id]

    nomes = [a.name for a in arquivos]
    sessao_id = db.abrir_sessao(nomes)
    prog["sessao_id"] = sessao_id

    pasta_saida = PDFS_DIR / job_id
    pasta_saida.mkdir(parents=True, exist_ok=True)

    # Pré-contar total de registros de todos os arquivos para progresso real
    totais_por_arquivo = []
    for arq in arquivos:
        try:
            totais_por_arquivo.append(_contar_registros(arq))
        except Exception:
            totais_por_arquivo.append(0)
    total_global = sum(totais_por_arquivo) or 1

    total_reg      = 0
    total_pag      = 0
    pdfs_gerados   = []
    registros_feitos = 0  # contador global para % real

    try:
        for idx, arquivo in enumerate(arquivos):
            if cancel_ev and cancel_ev.is_set():
                prog["status"] = "cancelado"
                db.registrar_log(sessao_id, "Geração cancelada pelo usuário.", "warn")
                db.fechar_sessao(sessao_id, "cancelado",
                                 total_registros=total_reg, total_paginas=total_pag,
                                 num_pdfs=len(pdfs_gerados), pasta_saida=str(pasta_saida))
                return

            prog["log"].append(f"📂 Processando: {arquivo.name}")
            db.registrar_log(sessao_id, f"Processando: {arquivo.name}", "info")

            ts        = datetime.now().strftime("%d-%m-%Y-%H%M")
            stem      = arquivo.stem
            nome_base = f"iptu-{ts}-{stem}"
            dest_pdf  = pasta_saida / f"{nome_base}.pdf"
            verso     = str(verso_path) if verso_path and verso_path.exists() \
                        else str(BASE_DIR / "static" / "img" / "iptu-verso.jpg")

            # total de registros deste arquivo para progresso granular
            total_este = totais_por_arquivo[idx] or 1
            base_pct   = (registros_feitos / total_global) * 100
            _reg_no_arquivo = [0]  # mutável para o closure

            def _log_fn(msg: str, tipo: str = "info", _idx=idx, _base=base_pct,
                        _tot=total_este, _gtot=total_global, _feitos=registros_feitos):
                prog["log"].append(msg)
                # Detectar mensagem de progresso por parte do motor
                # Ex: "  ✅ Parte 01/03: arquivo.pdf (2.1 MB) – 500 registros"
                m = re.search(r'–\s*(\d+)\s*registros', msg)
                if m:
                    regs_parte = int(m.group(1))
                    _reg_no_arquivo[0] += regs_parte
                    pct = _base + (_reg_no_arquivo[0] / _gtot) * 100
                    prog["percent"] = min(pct, 99)
                # Detectar log por registro ("📊 Total de registros : N")
                m2 = re.search(r'Total de registros\s*:\s*(\d+)', msg)
                if m2:
                    prog["log"]  # só para não otimizar o closure

            resultado = processar_arquivo(
                str(arquivo),
                str(dest_pdf),
                imagem_propaganda=verso,
                cancelar_flag=cancel_ev,
                log_fn=_log_fn,
            )

            if resultado:
                regs_arquivo = int(resultado)
                total_reg   += regs_arquivo
                registros_feitos += regs_arquivo

                pdfs_list = resultado.pdfs if hasattr(resultado, "pdfs") else [str(dest_pdf)]
                for pdf_path in pdfs_list:
                    pp = Path(pdf_path)
                    if not pp.exists():
                        continue
                    size_mb = pp.stat().st_size / 1048576
                    db.registrar_pdf(sessao_id, str(pp), size_mb)
                    db.registrar_log(sessao_id, f"✅ {pp.name} ({size_mb:.1f} MB)", "ok")
                    prog["log"].append(f"✅ PDF gerado: {pp.name} ({size_mb:.1f} MB)")
                    total_pag += regs_arquivo * 2
                    pdfs_gerados.append({
                        "nome":       pp.name,
                        "url":        f"/pdfs/{job_id}/{pp.name}",
                        "tamanho_mb": round(size_mb, 2),
                        "caminho":    str(pp),
                    })

            prog["percent"] = (registros_feitos / total_global) * 100

        prog["status"]          = "concluido"
        prog["percent"]         = 100
        prog["pdfs"]            = pdfs_gerados
        prog["job_dir"]         = str(pasta_saida)
        prog["total_registros"] = total_reg
        prog["total_paginas"]   = total_pag

        db.fechar_sessao(sessao_id, "concluido",
                         total_registros=total_reg, total_paginas=total_pag,
                         num_pdfs=len(pdfs_gerados), pasta_saida=str(pasta_saida))
        db.registrar_log(sessao_id, f"Concluído: {total_reg} registros, {len(pdfs_gerados)} PDFs.", "ok")

    except Exception as exc:
        prog["status"] = "erro"
        prog["erro"]   = str(exc)
        prog["log"].append(f"❌ Erro: {exc}")
        db.fechar_sessao(sessao_id, "erro", erro_msg=str(exc))
        db.registrar_log(sessao_id, f"Erro: {exc}", "err")
        print(traceback.format_exc())


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "ano": datetime.now().year}


@app.post("/api/gerar")
async def gerar(
    arquivos: list[UploadFile] = File(...),
    verso: Optional[UploadFile] = File(default=None),
):
    if not arquivos:
        raise HTTPException(400, "Nenhum arquivo enviado.")

    job_id     = str(uuid.uuid4())
    job_upload = UPLOAD_DIR / job_id
    job_upload.mkdir(parents=True, exist_ok=True)

    saved_txt: list[Path] = []
    for f in arquivos:
        if not f.filename.lower().endswith(".txt"):
            raise HTTPException(400, f"Arquivo inválido: {f.filename}. Apenas .txt são aceitos.")
        dest = job_upload / f.filename
        with open(dest, "wb") as out:
            shutil.copyfileobj(f.file, out)
        saved_txt.append(dest)

    verso_path: Optional[Path] = None
    if verso and verso.filename:
        ext = Path(verso.filename).suffix.lower()
        if ext in (".jpg", ".jpeg", ".png"):
            vp = job_upload / f"verso{ext}"
            with open(vp, "wb") as out:
                shutil.copyfileobj(verso.file, out)
            verso_path = vp

    cancel_ev = threading.Event()
    _cancel_flags[job_id] = cancel_ev
    _progress[job_id] = {
        "status":   "processando",
        "percent":  0,
        "log":      [],
        "pdfs":     [],
        "sessao_id": None,
    }

    t = threading.Thread(target=_worker_geracao, args=(job_id, saved_txt, verso_path), daemon=True)
    t.start()
    return {"job_id": job_id}


@app.get("/api/progresso/{job_id}")
def progresso(job_id: str):
    p = _progress.get(job_id)
    if not p:
        raise HTTPException(404, "Job não encontrado.")
    return p


@app.post("/api/cancelar/{job_id}")
def cancelar(job_id: str):
    ev = _cancel_flags.get(job_id)
    if not ev:
        raise HTTPException(404, "Job não encontrado.")
    ev.set()
    if job_id in _progress:
        _progress[job_id]["status"] = "cancelando"
    return {"ok": True}


@app.delete("/api/pdf")
def excluir_pdf(caminho: str):
    p = Path(caminho)
    if p.exists():
        p.unlink()
    db.marcar_pdf_excluido(caminho)
    return {"ok": True}


@app.get("/api/download-todos/{job_id}")
def download_todos(job_id: str):
    """Compacta todos os PDFs do job em ZIP e retorna para download."""
    pasta = PDFS_DIR / job_id
    if not pasta.exists():
        raise HTTPException(404, "Job não encontrado ou PDFs já removidos.")
    pdfs = sorted(pasta.glob("*.pdf"))
    if not pdfs:
        raise HTTPException(404, "Nenhum PDF disponível.")

    buf = _io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for pdf in pdfs:
            zf.write(pdf, pdf.name)
    buf.seek(0)

    ts       = datetime.now().strftime("%d-%m-%Y-%H%M")
    nome_zip = f"iptu-{ts}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{nome_zip}"'},
    )


@app.get("/api/historico")
def historico(limite: int = 100):
    return db.listar_sessoes(limite)


@app.get("/api/historico/{sessao_id}")
def detalhe_sessao(sessao_id: int):
    s = db.detalhe_sessao(sessao_id)
    if not s:
        raise HTTPException(404, "Sessão não encontrada.")
    return s


@app.get("/api/pdfs-sessao/{sessao_id}")
def pdfs_sessao(sessao_id: int):
    """Lista os PDFs ainda existentes em disco para uma sessão do histórico."""
    s = db.detalhe_sessao(sessao_id)
    if not s:
        raise HTTPException(404, "Sessão não encontrada.")
    resultado = []
    for p in s.get("pdfs", []):
        if p.get("excluido"):
            continue
        caminho = Path(p["caminho"])
        if caminho.exists():
            # Derivar job_id do caminho: data/pdfs/{job_id}/{nome}.pdf
            partes = caminho.parts
            try:
                idx_pdfs = list(partes).index("pdfs")
                job_id_pasta = partes[idx_pdfs + 1]
            except Exception:
                job_id_pasta = ""
            resultado.append({
                "nome":       p["nome"],
                "url":        f"/pdfs/{job_id_pasta}/{p['nome']}",
                "tamanho_mb": p.get("tamanho_mb", 0),
                "caminho":    str(caminho),
                "job_id":     job_id_pasta,
            })
    return resultado


@app.get("/api/download-sessao/{sessao_id}")
def download_sessao(sessao_id: int):
    """ZIP com todos os PDFs ainda existentes de uma sessão do histórico."""
    pdfs = pdfs_sessao(sessao_id)
    if not pdfs:
        raise HTTPException(404, "Nenhum PDF disponível para esta sessão.")

    buf = _io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in pdfs:
            pp = Path(p["caminho"])
            if pp.exists():
                zf.write(pp, pp.name)
    buf.seek(0)

    ts       = datetime.now().strftime("%d-%m-%Y-%H%M")
    nome_zip = f"iptu-sessao-{sessao_id}-{ts}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{nome_zip}"'},
    )


@app.delete("/api/historico")
def limpar_historico():
    """Apaga todas as sessões do banco e os PDFs em disco."""
    db.limpar_historico_completo()
    # Apaga todos os PDFs do volume
    if PDFS_DIR.exists():
        shutil.rmtree(PDFS_DIR)
        PDFS_DIR.mkdir(parents=True, exist_ok=True)
    return {"ok": True}


@app.delete("/api/purgar-ano-anterior")
def purgar_ano_anterior(ano: int = Query(...)):
    """Remove sessões e PDFs de anos anteriores ao informado."""
    sessoes = db.listar_sessoes(9999)
    removidos = 0
    for s in sessoes:
        data_str = s.get("iniciado_em", "")
        # formato DD/MM/YYYY HH:MM:SS
        try:
            ano_sessao = int(data_str.split("/")[2].split(" ")[0])
        except Exception:
            continue
        if ano_sessao < ano:
            det = db.detalhe_sessao(s["id"])
            if det:
                for p in det.get("pdfs", []):
                    try:
                        Path(p["caminho"]).unlink(missing_ok=True)
                    except Exception:
                        pass
            db.excluir_sessao(s["id"])
            removidos += 1
    return {"removidos": removidos}


@app.get("/api/estatisticas")
def estatisticas():
    return db.estatisticas()


@app.get("/api/verso-padrao")
def verso_padrao():
    return {"url": "/static/img/iptu-verso.jpg"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
