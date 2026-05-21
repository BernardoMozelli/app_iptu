#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Motor de Geração de PDF do IPTU – Prefeitura Municipal de Santa Luzia/MG
=======================================================================
Versão: 2.7 (Original com 7 Parcelas e Otimização de Layout)
"""

import os
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.graphics.barcode import code128
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ─── CONFIGURAÇÃO DA IMAGEM DA TESOURA ────────────────────────────────────────
# Caminho resolvido em relação a este arquivo (motor_iptu.py fica em app_iptu/app/)
# então sobe um nível para app_iptu/ e desce para static/img/
# Suporta PNG e JPG. ICO não é suportado pelo ReportLab — converta para PNG se necessário.
def _scissors_path() -> str:
    """Retorna o caminho absoluto da imagem da tesoura, compatível com bundle PyInstaller."""
    import sys as _sys
    # Modo bundle (PyInstaller): arquivos estão em _MEIPASS
    if getattr(_sys, "frozen", False) and hasattr(_sys, "_MEIPASS"):
        base = Path(_sys._MEIPASS)
    else:
        # motor_iptu.py está em app_iptu/app/ → sobe para app_iptu/
        base = Path(__file__).resolve().parent.parent
    # Tenta as extensões em ordem de preferência
    for ext in ("png", "jpg", "jpeg", "ico"):
        p = base / "static" / "img" / f"tesoura.{ext}"
        if p.exists():
            return str(p)
    return ""  # não encontrado — desenhar_frente tratará a ausência

SCISSORS_ICON_PATH = _scissors_path()


# ─── LAYOUT POSICIONAL (Mapeamento do arquivo .txt) ──────────────────────────
LAYOUT = {
    "NomeDestinatario":           (1,    80),
    "EnderecoCorres":             (81,   160),
    "BairroCorres":               (161,  200),
    "CidadeCorres":               (201,  220),
    "CepCorres":                  (221,  235),
    "UfCorres":                   (236,  237),
    "NomeContribuinte":           (238,  317),
    "EnderecoContrib":            (318,  397),
    "BairroContrib":              (398,  437),
    "CidadeContrib":              (438,  457),
    "CepContrib":                 (458,  472),
    "UfContrib":                  (473,  474),
    "EnderecoImovel":             (475,  554),
    "BairroImovel":               (555,  594),
    "CepImovel":                  (595,  609),
    "InfoComplementar":           (610,  709),
    "RefImovel":                  (710,  769),
    "CodigoLoteamento":           (770,  773),
    "ZonaUrbana":                 (774,  783),
    "DataEmissao":                (784,  793),
    "Exercicio":                  (794,  797),
    "InscricaoCadastral":         (798,  827),
    "InscricaoCadastralAnterior": (828,  857),
    "EspecificacaoReceita":       (858,  867),
    "Secao":                      (868,  873),
    "Aliquota":                   (904,  909),
    "AreaTerreno":                (910,  929),
    "ValorVenal":                 (930,  949),
    "FracaoTerreno":              (950,  969),
    "ValorTerreno":               (970,  989),
    "UsoImovel":                  (874,  973),
    "AreaEdificada":              (990,  1009),
    "ValorEdificacao":            (1010, 1029),
    "Testada":                    (1042, 1053),
    "IPTU_TCRS":                  (1054, 1073),
    "TxExped":                    (1074, 1093),
    "TxColLixo":                  (1094, 1113),
    "ContrIlumPublica":           (1114, 1133),
    "TotalaPagarSDesconto":       (1134, 1153),
    "TotalaPagarSTxExpDesc":      (1154, 1173),
    "Desconto":                   (1174, 1185),
    "TotalaPagarCDesconto":       (1186, 1205),
    "TotalaPagarExtenso":         (1206, 1355),
    "DescontoProgramado":         (1356, 1375),
    "MensDebitoAnterior":         (1376, 1475),
}


# ─── LAYOUT DAS PARCELAS (Cota Única + 6 Parcelas) ────────────────────────────
PARCELAS_LAYOUT = [
    (1476, 1481, 1525, 1535, 1548, 1561, 1574, 1587, 1607, 1627, 1647, 1667, 1687, 1707),
    (1720, 1725, 1769, 1779, 1792, 1805, 1818, 1831, 1851, 1871, 1891, 1911, 1931, 1951),
    (1964, 1969, 2013, 2023, 2036, 2049, 2062, 2075, 2095, 2115, 2135, 2155, 2175, 2195),
    (2208, 2213, 2257, 2267, 2280, 2293, 2306, 2319, 2339, 2359, 2379, 2399, 2419, 2439),
    (2452, 2457, 2501, 2511, 2524, 2537, 2550, 2563, 2583, 2603, 2623, 2643, 2663, 2683),
    (2696, 2701, 2745, 2755, 2768, 2781, 2794, 2807, 2827, 2847, 2867, 2887, 2907, 2927),
    (2940, 2945, 2989, 2999, 3012, 3025, 3038, 3051, 3071, 3091, 3111, 3131, 3151, 3171),
]

PARCELA_NOMES = ["Única", "1ª", "2ª", "3ª", "4ª", "5ª", "6ª"]

# ─── TAMANHOS DOS CAMPOS DE PARCELAS ──────────────────────────────────────────
TAM_NUMERO = 5
TAM_BARRAS = 44
TAM_VENC = 10
TAM_BLOCO = 13
TAM_VALOR = 20
TAM_TOTAL = 13


# ─── CORES DO DOCUMENTO ──────────────────────────────────────────────────────
AZUL = colors.HexColor("#0052A3")
AZUL_ESC = colors.HexColor("#003D7A")
VERDE = colors.HexColor("#7BC043")
LARANJA = colors.HexColor("#F39200")
CINZA_BG = colors.HexColor("#F5F7FA")
CINZA_LN = colors.HexColor("#E2E8F0")
CINZA_TXT = colors.HexColor("#64748B")
PRETO = colors.HexColor("#1A2A3A")
BRANCO = colors.white


# ─── FUNÇÕES AUXILIARES ──────────────────────────────────────────────────────

def _campo(linha, ini, fim):
    """
    Extrai campo posicional por posicao de BYTE (nao char).
    Aceita bytes ou str. Quando bytes, decodifica em latin-1 para
    preservar acentos sem deslocamento de posicao.
    """
    if isinstance(linha, (bytes, bytearray)):
        return linha[ini - 1:fim].decode("latin-1", errors="replace").strip()
    return linha[ini - 1:fim].strip()

def parse_linha(linha):
    dados = {nome: _campo(linha, ini, fim) for nome, (ini, fim) in LAYOUT.items()}
    dados["parcelas"] = []
    
    for idx, off in enumerate(PARCELAS_LAYOUT):
        n, b, v, b1, b2, b3, b4, vp, vj, vc, vm, vr, vd, vt = off
        barras = _campo(linha, b, b + TAM_BARRAS - 1)
        venc = _campo(linha, v, v + TAM_VENC - 1)
        
        if not barras and not venc:
            continue
        
        dados["parcelas"].append({
            "nome": PARCELA_NOMES[idx],
            "numero": _campo(linha, n, n + TAM_NUMERO - 1),
            "barras": barras,
            "venc": venc,
            "bloco1": _campo(linha, b1, b1 + TAM_BLOCO - 1),
            "bloco2": _campo(linha, b2, b2 + TAM_BLOCO - 1),
            "bloco3": _campo(linha, b3, b3 + TAM_BLOCO - 1),
            "bloco4": _campo(linha, b4, b4 + TAM_BLOCO - 1),
            "vr_parc": _campo(linha, vp, vp + TAM_VALOR - 1),
            "vr_juros": _campo(linha, vj, vj + TAM_VALOR - 1),
            "vr_corr": _campo(linha, vc, vc + TAM_VALOR - 1),
            "vr_mult": _campo(linha, vm, vm + TAM_VALOR - 1),
            "vr_pagar": _campo(linha, vr, vr + TAM_VALOR - 1),
            "vr_desc": _campo(linha, vd, vd + TAM_VALOR - 1),
            "vr_total": _campo(linha, vt, vt + TAM_TOTAL - 1),
        })
    return dados

def fmt(v):
    v = v.strip()
    return v if v else "-"

def fmt_cep(cep):
    c = cep.strip().replace("-", "").replace(".", "")
    return f"{c[:5]}-{c[5:]}" if len(c) == 8 else cep.strip()

def _stripe(c, x, y, w, h=2*mm):
    seg = w / 3
    for i, cor in enumerate([AZUL, VERDE, LARANJA]):
        c.setFillColor(cor)
        c.rect(x + i * seg, y, seg, h, fill=1, stroke=0)

def _box(c, x, y, w, h, fill, stroke=None, sw=0.5):
    c.setFillColor(fill)
    if stroke:
        c.setStrokeColor(stroke)
        c.setLineWidth(sw)
        c.rect(x, y, w, h, fill=1, stroke=1)
    else:
        c.rect(x, y, w, h, fill=1, stroke=0)


# ─── DESENHO DA FRENTE DO BOLETO ─────────────────────────────────────────────

def desenhar_frente(c, dados, logo_path=None):
    W, H = A4
    MG = 10 * mm
    CW = W - 2 * MG
    
    # Fundo branco
    c.setFillColor(BRANCO)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    
    # ─── CABEÇALHO ────────────────────────────────────────────────────────────
    _stripe(c, MG, H - MG - 3*mm, CW, 3*mm)
    
    cab_h = 18 * mm
    cab_y = H - MG - 3*mm - cab_h
    _box(c, MG, cab_y, CW, cab_h, AZUL)
    
    text_x = MG + 4*mm
    if logo_path and os.path.exists(logo_path):
        try:
            logo_h = 14 * mm
            logo_w = 66 * mm
            c.drawImage(logo_path, MG + 3*mm, cab_y + (cab_h - logo_h) / 2,
                        width=logo_w, height=logo_h,
                        preserveAspectRatio=True, anchor="w", mask="auto")
            text_x = MG + 72*mm
        except:
            pass
    
    exercicio = dados.get("Exercicio", "2026")
    emissao = dados.get("DataEmissao", "")
    
    c.setFillColor(BRANCO)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(text_x, cab_y + cab_h - 7*mm, "SECRETARIA MUNICIPAL DE FINANÇAS")
    c.setFont("Helvetica", 9)
    c.drawString(text_x, cab_y + cab_h - 12*mm, "Imposto Predial e Territorial Urbano — IPTU / TCRS")
    
    c.setFillColor(LARANJA)
    c.setFont("Helvetica-Bold", 22)
    c.drawRightString(W - MG - 3*mm, cab_y + cab_h - 11*mm, exercicio)
    
    c.setFillColor(colors.HexColor("#FFD580"))
    c.setFont("Helvetica", 8)
    c.drawRightString(W - MG - 3*mm, cab_y + cab_h - 15*mm, f"Emissão: {emissao}")
    
    Y = cab_y - 2*mm
    
    # ─── SEÇÃO: CONTRIBUINTE / DESTINATÁRIO ────────────────────────────────
    sec_h = 20 * mm
    Y -= sec_h
    
    _box(c, MG, Y, CW, sec_h, CINZA_BG, CINZA_LN)
    c.setFillColor(AZUL)
    c.rect(MG, Y, 2.5, sec_h, fill=1, stroke=0)
    
    c.setFillColor(AZUL)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(MG + 4*mm, Y + sec_h - 4.5*mm, "CONTRIBUINTE")
    
    nome = dados.get("NomeContribuinte") or dados.get("NomeDestinatario", "")
    c.setFillColor(PRETO)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(MG + 4*mm, Y + sec_h - 9.5*mm, nome[:70])
    
    c.setFillColor(CINZA_TXT)
    c.setFont("Helvetica", 9)
    end_c = dados.get("EnderecoContrib", "")
    bairro_c = dados.get("BairroContrib", "")
    cidade_c = dados.get("CidadeContrib", "")
    uf_c = dados.get("UfContrib", "")
    cep_c = fmt_cep(dados.get("CepContrib", ""))
    
    c.drawString(MG + 4*mm, Y + sec_h - 14*mm, end_c[:80])
    c.drawString(MG + 4*mm, Y + sec_h - 18*mm, f"{bairro_c}  –  {cidade_c} / {uf_c}   CEP: {cep_c}")
    
    inscr = dados.get("InscricaoCadastral", "")
    c.setFillColor(CINZA_TXT)
    c.setFont("Helvetica", 7)
    c.drawRightString(W - MG - 3*mm, Y + sec_h - 14*mm, "INSCRIÇÃO CADASTRAL")
    
    c.setFillColor(AZUL)
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(W - MG - 3*mm, Y + sec_h - 18*mm, inscr)
    
    Y -= 2*mm
    
    # ─── SEÇÃO: DADOS DO IMÓVEL ───────────────────────────────────────────
    imo_h = 20 * mm
    Y -= imo_h
    
    _box(c, MG, Y, CW, imo_h, BRANCO, CINZA_LN)
    c.setFillColor(VERDE)
    c.rect(MG, Y, 2.5, imo_h, fill=1, stroke=0)
    
    c.setFillColor(VERDE)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(MG + 4*mm, Y + imo_h - 4.5*mm, "DADOS DO IMÓVEL")
    
    end_i = dados.get("EnderecoImovel", "")
    bairro_i = dados.get("BairroImovel", "")
    cep_i = fmt_cep(dados.get("CepImovel", ""))
    ref = dados.get("RefImovel", "").strip()
    
    c.setFillColor(PRETO)
    c.setFont("Helvetica", 9)
    c.drawString(MG + 4*mm, Y + imo_h - 9.5*mm, end_i[:75])
    
    c.setFillColor(CINZA_TXT)
    c.setFont("Helvetica", 8)
    c.drawString(MG + 4*mm, Y + imo_h - 14*mm, f"Bairro: {bairro_i} CEP: {cep_i}")
    c.drawString(MG + 4*mm, Y + imo_h - 18*mm, f"Ref: {ref[:75]}")
    
    # ─── SEÇÃO: COMPOSIÇÃO DOS TRIBUTOS ───────────────────────────────────
    trib_h = 28 * mm
    Y -= trib_h
    
    _box(c, MG, Y, CW, trib_h, CINZA_BG, CINZA_LN)
    c.setFillColor(AZUL_ESC)
    c.rect(MG, Y + trib_h - 5.5*mm, CW, 5.5*mm, fill=1, stroke=0)
    
    c.setFillColor(BRANCO)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(MG + 4*mm, Y + trib_h - 4*mm, "COMPOSIÇÃO DOS TRIBUTOS")
    
    col_labels = ["IPTU", "Tx. Exped.", "Tx. Lixo", "C. Ilum.", "S/ Desc.", "Desconto", "Total c/ Desconto"]
    col_vals = [
        fmt(dados.get("IPTU_TCRS", "")), fmt(dados.get("TxExped", "")), fmt(dados.get("TxColLixo", "")),
        fmt(dados.get("ContrIlumPublica", "")), fmt(dados.get("TotalaPagarSDesconto", "")),
        fmt(dados.get("Desconto", "")), fmt(dados.get("TotalaPagarCDesconto", ""))
    ]
    
    n_cols = len(col_labels)
    col_w = CW / n_cols
    cols_y = Y + 8*mm
    cols_h = 14.5*mm
    
    for i, (lbl, val) in enumerate(zip(col_labels, col_vals)):
        x = MG + i * col_w
        is_total = (i == 6)
        
        if is_total:
            _box(c, x, cols_y, col_w, cols_h, AZUL, BRANCO, 2)
            c.setFillColor(BRANCO)
            c.setFont("Helvetica-Bold", 7)
            c.drawCentredString(x + col_w / 2, cols_y + 10*mm, lbl)
            c.setFillColor(LARANJA)
            c.setFont("Helvetica-Bold", 11)
            # Truncar valor se muito longo
            val_display = val if len(val) <= 10 else val[:10]
            c.drawCentredString(x + col_w / 2, cols_y + 3*mm, f"R$ {val_display}")
        else:
            c.setFillColor(CINZA_TXT)
            c.setFont("Helvetica-Bold", 7.5)
            c.drawCentredString(x + col_w / 2, cols_y + 12*mm, lbl)
            c.setFillColor(PRETO)
            c.setFont("Helvetica-Bold", 8.5)
            # Truncar valor se muito longo
            val_display = val if len(val) <= 12 else val[:12]
            c.drawCentredString(x + col_w / 2, cols_y + 3.5*mm, f"R$ {val_display}")
        
        if i > 0 and not is_total:
            c.setStrokeColor(CINZA_LN)
            c.setLineWidth(0.4)
            c.line(x, cols_y + 1.5*mm, x, cols_y + cols_h - 1.5*mm)
    
    c.setStrokeColor(CINZA_LN)
    c.setLineWidth(0.5)
    c.line(MG + 2*mm, cols_y, MG + CW - 2*mm, cols_y)
    
    aliq = fmt(dados.get("Aliquota", ""))
    area_t = fmt(dados.get("AreaTerreno", ""))
    area_e = fmt(dados.get("AreaEdificada", ""))
    v_venal = fmt(dados.get("ValorVenal", ""))
    uso = fmt(dados.get("UsoImovel", ""))
    
    c.setFillColor(CINZA_TXT)
    c.setFont("Helvetica", 8)
    det = (f"Alíquota: {aliq}  |  Área Terreno: {area_t} m²  |  Área Edificada: {area_e} m²  |  Valor Venal: R$ {v_venal}  |  Uso: {uso}")
    # Truncar com cuidado para não cortar no meio de palavras
    det_display = det[:140] if len(det) > 140 else det
    c.drawString(MG + 4*mm, Y + 3.5*mm, det_display)
    
    Y -= 2*mm
    
    # ─── SEÇÃO: INSTRUÇÕES ────────────────────────────────────────────────
    inst_h = 14*mm
    Y -= inst_h
    
    _box(c, MG, Y, CW, inst_h, BRANCO, CINZA_LN, 0.4)
    
    c.setFillColor(PRETO)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(MG + 3*mm, Y + 10.5*mm, "Sr(a) Caixa:")
    c.setFont("Helvetica", 7.5)
    c.drawString(MG + 20*mm, Y + 10.5*mm, "- Não receber após vencimento.")
    c.drawString(MG + 3*mm, Y + 6.5*mm, "Sr. (a) Contribuinte os beneficios da lei complementar nº3.160/2010 e as impugnações deverão se apresentada até a data")
    c.drawString(MG + 3*mm, Y + 3.5*mm, "de vencimento da cota unica ou 1º parcela.")
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(MG + 3*mm, Y + 0.5*mm, "Pagável: Bancos do Brasil, Itau, Bradesco, Correios, CEF, Casas Lotéricas e SICOOB.")
    c.drawString(MG + 3*mm, Y + 0.2*mm, "")
    Y -= 2*mm
    
    # ─── SEÇÃO: PARCELAS / BOLETOS ────────────────────────────────────────
    parcelas = dados.get("parcelas", [])
    
    if not parcelas:
        _rodape(c, W, H, MG, dados)
        return
    
    parcelas.reverse()
    
    parc_cab_h = 6*mm
    Y -= parc_cab_h
    
    _box(c, MG, Y, CW, parc_cab_h, AZUL_ESC)
    c.setFillColor(BRANCO)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(MG + 4*mm, Y + 1.5*mm, "PARCELAS / BOLETOS PARA PAGAMENTO")
    
    rod_y = 5*mm
    rodape_h = 12*mm
    espaco = Y - (rod_y + rodape_h)
    n_parc = len(parcelas)
    
    parc_h = espaco / n_parc if n_parc > 0 else 0
    
    # 👉 TRAVA 1: Impede que a caixa da parcela ocupe a folha toda
    # Aumentado para permitir que ocupe mais espaço na folha A4
    if parc_h > 45 * mm:
        parc_h = 45 * mm
    
    for idx, parc in enumerate(parcelas):
        y_ini = Y - idx * parc_h
        y_fim = y_ini - parc_h
        bg = CINZA_BG if idx % 2 == 0 else BRANCO
        
        _box(c, MG, y_fim, CW, parc_h, bg, CINZA_LN, 0.4)
        
        if idx > 0:
            c.setStrokeColor(CINZA_TXT)
            c.setLineWidth(0.6)
            c.setDash(3, 3)
            c.line(MG, y_ini, W - MG, y_ini)
            c.setDash()
            
            img_w = 3 * mm
            img_h = 3 * mm
            _desenhada = False
            if SCISSORS_ICON_PATH:
                try:
                    _path_usar = SCISSORS_ICON_PATH
                    # ICO não é suportado pelo ReportLab — converter para PNG em memória
                    if SCISSORS_ICON_PATH.lower().endswith(".ico"):
                        from PIL import Image as _PILImage
                        import io as _io
                        with _PILImage.open(SCISSORS_ICON_PATH) as _im:
                            _buf = _io.BytesIO()
                            _im.save(_buf, format="PNG")
                            _buf.seek(0)
                            _path_usar = _buf
                    from reportlab.lib.utils import ImageReader as _IR
                    c.drawImage(_IR(_path_usar), W / 2 - img_w / 2, y_ini - img_h / 2,
                                width=img_w, height=img_h, mask='auto')
                    _desenhada = True
                except Exception:
                    pass
            if not _desenhada:
                # Fallback: símbolo ✂ em Unicode via Helvetica
                c.setFillColor(CINZA_TXT)
                c.setFont("Helvetica", 7)
                c.drawCentredString(W / 2, y_ini - 2.5 * mm, "✂")
        
        if parc['nome'] == "Única":
            badge_col = AZUL
        else:
            badge_col = VERDE
        
        badge_w = 22*mm
        badge_h = 5.5*mm
        y_badge = y_ini - 1.5*mm - badge_h
        
        _box(c, MG + 2*mm, y_badge, badge_w, badge_h, badge_col)
        
        c.setFillColor(BRANCO)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawCentredString(MG + 13*mm, y_badge + 1.5*mm, f"Parcela {parc['nome']}")
        
        c.setFillColor(PRETO)
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(MG + 26*mm, y_badge + 1.5*mm, f"Venc.: {parc['venc']}")
        
        valor_exibido = parc['vr_pagar']
        if parc['nome'] == "Única":
            valor_exibido = dados.get("TotalaPagarCDesconto", valor_exibido)
        
        c.setFillColor(AZUL)
        c.setFont("Helvetica-Bold", 11)
        c.drawRightString(W - MG - 3*mm, y_badge + 1.5*mm, f"R$ {fmt(valor_exibido)}")
        
        blocos = "   ".join(filter(None, [parc.get("bloco1", ""), parc.get("bloco2", ""), parc.get("bloco3", ""), parc.get("bloco4", "")]))
        
        c.setFillColor(CINZA_TXT)
        c.setFont("Helvetica", 7.5)
        y_linha_dig = y_badge - 3.5*mm
        c.drawString(MG + 3*mm, y_linha_dig, f"Linha Digitável:  {blocos}")
        
        c.setFont("Helvetica", 6)
        c.setFillColor(CINZA_TXT)
        det_parc = (f"Parcela: R$ {fmt(parc['vr_parc'])}   Juros: R$ {fmt(parc['vr_juros'])}   "
                   f"Correção: R$ {fmt(parc['vr_corr'])}   Multa: R$ {fmt(parc['vr_mult'])}   Desconto: R$ {fmt(parc['vr_desc'])}")
        y_detalhes = y_fim + 1.5*mm
        c.drawString(MG + 3*mm, y_detalhes, det_parc)
        
        # 👉 TRAVA 2: Altura do Código de Barras travada entre 3.5mm e 16mm
        barras = parc.get("barras", "").strip()
        bc_h = y_linha_dig - y_detalhes - 4*mm
        bc_y = y_detalhes + 3*mm 
        
        if bc_h < 3.5*mm: 
            bc_h = 3.5*mm
        elif bc_h > 16*mm: 
            bc_h = 16*mm
            bc_y = y_linha_dig - bc_h - 1.5*mm 

        if barras and len(barras) >= 10:
            try:
                bc = code128.Code128(value=barras, barWidth=1.1, barHeight=bc_h, humanReadable=False, quiet=False)
                bc_x = MG + (CW - bc.width) / 2
                bc.drawOn(c, bc_x, bc_y)
            except:
                pass
    
    _rodape(c, W, H, MG, dados)

# ─── DESENHO DO VERSO DO BOLETO ──────────────────────────────────────────────
def desenhar_verso(c, dados, imagem_propaganda, exercicio="2026"):
    W, H = A4
    MG = 8*mm
    c.setFillColor(BRANCO)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    
    if imagem_propaganda and os.path.exists(imagem_propaganda):
        try:
            c.drawImage(imagem_propaganda, 0, 0, width=W, height=H, preserveAspectRatio=False)
        except:
            pass
    
    nome_dest = (dados.get("NomeDestinatario") or "").strip()
    end_dest = (dados.get("EnderecoCorres") or "").strip()
    bairro_dest = (dados.get("BairroCorres") or "").strip()
    cidade_dest = (dados.get("CidadeCorres") or "").strip()
    cep_dest = (dados.get("CepCorres") or "").strip()
    uf_dest = (dados.get("UfCorres") or "").strip()
    cep_formatado = fmt_cep(cep_dest)
    
    # ────────────────────────────────────────────────────────────────────────
    # Calibragem do quadrado branco para endereço
    # ────────────────────────────────────────────────────────────────────────
    pos_x = 93 * mm   # Margem esquerda do quadrado
    pos_y = 116.5 * mm  # Posição da primeira linha (Nome)
    entrelinha = 4.5 * mm
    W_disp = W - pos_x - 8 * mm  # largura disponível até a margem direita

    def _quebrar_texto(texto, fonte, tamanho, largura_max):
        """
        Quebra o texto em linhas que caibam dentro de largura_max (em pontos).
        Divide por palavras para não cortar no meio de uma palavra.
        Retorna lista de strings.
        """
        c.setFont(fonte, tamanho)
        palavras = texto.split()
        linhas = []
        atual = ""
        for palavra in palavras:
            candidato = (atual + " " + palavra).strip()
            if c.stringWidth(candidato, fonte, tamanho) <= largura_max:
                atual = candidato
            else:
                if atual:
                    linhas.append(atual)
                # Se uma única palavra já é grande demais, inclui mesmo assim
                atual = palavra
        if atual:
            linhas.append(atual)
        return linhas if linhas else [""]

    c.setFillColor(PRETO)

    # Nome do destinatário — quebra em até 2 linhas se necessário
    linhas_nome = _quebrar_texto(nome_dest, "Helvetica-Bold", 9, W_disp)
    linhas_nome = linhas_nome[:2]  # máximo 2 linhas para o nome

    c.setFont("Helvetica-Bold", 9)
    for i, linha in enumerate(linhas_nome):
        c.drawString(pos_x, pos_y - i * entrelinha, linha)

    # Offset: as linhas seguintes descem conforme o número de linhas do nome
    offset = len(linhas_nome) * entrelinha

    c.setFont("Helvetica", 9)
    c.drawString(pos_x, pos_y - offset,                 end_dest[:55])
    c.drawString(pos_x, pos_y - offset - entrelinha,    bairro_dest[:55])
    c.drawString(pos_x, pos_y - offset - 2 * entrelinha, f"{cidade_dest} / {uf_dest}")
    c.drawString(pos_x, pos_y - offset - 3 * entrelinha, f"CEP: {cep_formatado}")
    
    _rodape(c, W, H, 10*mm, dados)

# ─── RODAPÉ DO DOCUMENTO ─────────────────────────────────────────────────────
def _rodape(c, W, H, MG, dados):
    rod_h = 12*mm
    rod_y = 5*mm
    _stripe(c, MG, rod_y + rod_h - 1.5*mm, W - 2*MG, 1.5*mm)
    _box(c, MG, rod_y, W - 2*MG, rod_h - 1.5*mm, AZUL_ESC)
    c.setFillColor(BRANCO)
    c.setFont("Helvetica", 7.5)
    c.drawCentredString(W / 2, rod_y + 6.5*mm, "Prefeitura Municipal de Santa Luzia - MG  |  www.santaluzia.mg.gov.br  |  IPTU 2026")
    c.setFont("Helvetica-Bold", 7.5)
    c.drawCentredString(W / 2, rod_y + 2.5*mm, "Desenvolvido pela Secretaria Municipal de Planejamento, Ciência, Tecnologia e Inovação")
    emissao = dados.get('DataEmissao', '')
    if emissao:
        c.setFont("Helvetica", 5.5)
        c.drawRightString(W - MG - 3*mm, rod_y + 1.5*mm, f"Emitido em: {emissao}")

# ─── PROCESSAMENTO DO ARQUIVO ───────────────────────────────────────────────

# Quantos registros por PDF parcial. 2.000 gera arquivos de ~80–120 MB cada,
# fáceis de abrir e imprimir. Ajuste conforme a RAM disponível no servidor.
REGISTROS_POR_PARTE = 2000


def processar_arquivo(
    arquivo_dados,
    arquivo_saida,
    imagem_propaganda,
    encoding="utf-8",  # mantido por compatibilidade, ignorado (leitura e feita em binario)
    logo_path=None,
    registros_por_parte=REGISTROS_POR_PARTE,
    cancelar_flag=None,  # threading.Event opcional; set() interrompe o processamento
    log_fn=None,          # callable(msg, tipo) opcional — substitui print() para SSE
):
    """
    Processa arquivo de dados posicional e gera um ou mais PDFs frente/verso.
    O arquivo e lido em modo binario para garantir posicionamento correto mesmo
    em registros com caracteres acentuados (latin-1), que deslocariam posicoes
    se lidos como UTF-8.

    Para arquivos com mais de `registros_por_parte` registros, o resultado é
    dividido automaticamente em partes numeradas:
        IPTU_20260428_001_parte_01.pdf
        IPTU_20260428_001_parte_02.pdf
        …

    Retorna uma tupla  (total_registros, lista_de_pdfs_gerados).
    Para manter compatibilidade com código antigo que só captura o primeiro
    valor, o retorno é um objeto _Resultado que também se comporta como int.
    """
    # ── Registrar fontes DejaVu (silencioso se ausente) ──────────────────────
    try:
        pdfmetrics.registerFont(TTFont("DejaVuSans",      "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
        pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))
    except Exception:
        pass

    if not os.path.exists(arquivo_dados):
        raise FileNotFoundError(f"Arquivo não encontrado: {arquivo_dados}")

    Path(arquivo_saida).parent.mkdir(parents=True, exist_ok=True)

    arquivo_base = str(arquivo_saida).replace(".pdf", "")

    # ── Primeira passagem: contar registros e capturar exercício ─────────────
    # Lemos apenas a 1ª linha para o exercício; o total vem do wc-l equivalente
    # em Python para não carregar tudo em RAM.
    exercicio = "2026"
    total = 0
    # Leitura em modo BINARIO: posicionamento por byte, imune a acentos latin-1
    # que deslocariam posicoes quando lidos como utf-8 com errors=ignore/replace
    with open(arquivo_dados, "rb") as f:
        for i, linha in enumerate(f):
            if not linha.strip():
                continue
            if i == 0:
                ex = linha[793:797].decode("latin-1", errors="replace").strip()
                if ex.isdigit() and len(ex) == 4:
                    exercicio = ex
            total += 1

    if total == 0:
        raise ValueError("Nenhum registro encontrado no arquivo.")

    # ── Calcular número de partes necessárias ────────────────────────────────
    num_partes = max(1, (total + registros_por_parte - 1) // registros_por_parte)

    # Helper: usa log_fn (SSE) se disponível, senão print normal
    def _log(msg, tipo="info"):
        if log_fn is not None:
            try:
                log_fn(msg, tipo)
            except Exception:
                pass
        print(msg)

    _log(f"📊 Total de registros : {total}", "info")
    _log(f"📦 Registros por parte: {registros_por_parte}", "info")
    _log(f"🗂️  Partes a gerar     : {num_partes}", "info")

    pdfs_gerados = []

    # ── Segunda passagem: streaming — nunca mais de registros_por_parte em RAM
    with open(arquivo_dados, "rb") as f:
        parte = 1
        contador_parte = 0
        c = None

        def _abrir_canvas(n_parte):
            sufixo = f"_parte_{n_parte:02d}" if num_partes > 1 else ""
            caminho = f"{arquivo_base}{sufixo}.pdf"
            cv = pdfcanvas.Canvas(caminho, pagesize=A4, compress=1)
            cv.setTitle(
                f"IPTU {exercicio} – Prefeitura Municipal de Santa Luzia"
                + (f" (Parte {n_parte}/{num_partes})" if num_partes > 1 else "")
            )
            return cv, caminho

        def _fechar_canvas(cv, caminho, n_reg, n_parte):
            cv.save()
            mb = os.path.getsize(caminho) / (1024 * 1024)
            pdfs_gerados.append(caminho)
            _log(f"  ✅ Parte {n_parte:2d}/{num_partes}: {os.path.basename(caminho)} ({mb:.1f} MB) – {n_reg} registros", "ok")

        c, caminho_atual = _abrir_canvas(parte)

        cancelado = False
        for linha in f:
            if not linha.strip():
                continue

            # Verificar sinal de cancelamento a cada registro
            if cancelar_flag is not None and cancelar_flag.is_set():
                cancelado = True
                break

            dados = parse_linha(linha.rstrip(b"\r\n"))
            desenhar_frente(c, dados, logo_path=logo_path)
            c.showPage()
            desenhar_verso(c, dados, imagem_propaganda, exercicio)
            c.showPage()
            contador_parte += 1

            # Fechar parte e abrir nova quando atingir o limite
            if contador_parte >= registros_por_parte:
                _fechar_canvas(c, caminho_atual, contador_parte, parte)
                parte += 1
                contador_parte = 0
                c, caminho_atual = _abrir_canvas(parte)

        if cancelado:
            # Descartar canvas parcial sem salvar
            try:
                c._doc = None  # evita flush automatico
            except Exception:
                pass
            _log(f"  🛑 Cancelado após {contador_parte} registros da parte {parte}.", "warn")
        else:
            # Fechar a ultima parte (pode ter menos que registros_por_parte)
            if contador_parte > 0:
                _fechar_canvas(c, caminho_atual, contador_parte, parte)

    return _Resultado(total, pdfs_gerados)


class _Resultado(int):
    """
    Retorno de processar_arquivo.
    Comporta-se como int (total de registros) para compatibilidade,
    mas expõe também .pdfs (lista de caminhos) e .total.
    """
    def __new__(cls, total, pdfs):
        obj = super().__new__(cls, total)
        obj.total = total
        obj.pdfs = pdfs
        return obj