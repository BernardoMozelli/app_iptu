# IPTU Gerador — Versão Docker (React + FastAPI) v3.0

**Prefeitura Municipal de Santa Luzia / MG**  
Secretaria Municipal de Planejamento, Ciência, Tecnologia e Inovação  
**Autor: Bernardo Mozelli de Medeiros**

---

## Arquitetura

```
Navegador (http://[servidor])
        │ HTTP :80
┌───────▼────────────────────────────────────┐
│  frontend — nginx + React (Vite) build     │
│  • SPA React 18, drag-and-drop, log ao     │
│    vivo via polling, download de PDFs      │
│  • Proxy /api/* e /pdfs/* → backend:8000   │
└───────────────────┬────────────────────────┘
                    │ HTTP interno (iptu_net)
┌───────────────────▼────────────────────────┐
│  backend — Python 3.12 + FastAPI           │
│  • motor_iptu.py  ← ORIGINAL, intacto     │
│  • db.py          ← ORIGINAL, intacto     │
│  • main.py        ← API REST (nova)        │
│  Volume: iptu_data → /app/data             │
│    ├── pdfs/     (PDFs gerados)            │
│    ├── uploads/  (arquivos temp)           │
│    └── logs/     (iptu.db SQLite)          │
└────────────────────────────────────────────┘
```

## Pré-requisitos

- Docker 24+ com Docker Compose v2
- Porta 80 livre no servidor

## Subir o sistema

```bash
cd iptu-docker
docker compose up --build -d
```

Acesse: **http://[IP-DO-SERVIDOR]**

## Parar / remover

```bash
docker compose down        # para containers (dados preservados)
docker compose down -v     # para e apaga dados (PDFs, banco)
```

## Estrutura de arquivos

```
iptu-docker/
├── backend/
│   ├── Dockerfile
│   ├── main.py            ← API FastAPI (nova)
│   ├── motor_iptu.py      ← Motor PDF (ORIGINAL, intacto)
│   ├── db.py              ← SQLite (ORIGINAL, intacto)
│   ├── requirements.txt
│   └── static/img/        ← logos, iptu-verso.jpg
├── frontend/
│   ├── Dockerfile         ← multi-stage: Vite build → nginx
│   ├── nginx.conf         ← proxy /api → backend, SPA routing
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   └── src/
│       ├── App.jsx                  ← orquestrador principal
│       ├── main.jsx
│       ├── components/
│       │   ├── Header.jsx           ← cabeçalho + barra tricolor
│       │   ├── Card.jsx             ← card reutilizável
│       │   ├── FileDropzone.jsx     ← drag-and-drop .txt / imagem
│       │   ├── ProgressPanel.jsx    ← barra + log de terminal
│       │   ├── ResultsPanel.jsx     ← lista PDFs + download
│       │   └── HistoricoPanel.jsx   ← histórico de sessões
│       └── utils/
│           └── api.js               ← client Axios
└── docker-compose.yml
```

## API REST (porta 8000, acesso via /api no nginx)

| Rota | Método | Descrição |
|---|---|---|
| `/api/health` | GET | Health check |
| `/api/gerar` | POST | Inicia geração (multipart: arquivos + verso) |
| `/api/progresso/{job_id}` | GET | Status, % e log do job em andamento |
| `/api/cancelar/{job_id}` | POST | Cancela geração em curso |
| `/api/pdf` | DELETE | Exclui PDF gerado |
| `/api/historico` | GET | Lista sessões do banco SQLite |
| `/api/estatisticas` | GET | Totais globais de sessões e registros |

## Fluxo de uso

1. Abra `http://[IP-DO-SERVIDOR]`
2. Arraste os arquivos `.txt` exportados do ERP Supernova
3. (Opcional) Substitua a imagem do verso
4. Clique em **Gerar PDFs**
5. Acompanhe o progresso no log ao vivo
6. Baixe os PDFs gerados diretamente pelo navegador

## Persistência de dados

PDFs e banco SQLite ficam no volume Docker `iptu_data`.

```bash
# Backup manual
docker run --rm -v iptu_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/iptu_backup_$(date +%Y%m%d).tar.gz /data
```

## Arquivos originais preservados

| Arquivo | Origem | Status |
|---|---|---|
| `motor_iptu.py` | app_iptu_flet/app/ | ✅ 100% intacto |
| `db.py` | app_iptu_flet/app/ | ✅ 100% intacto |

## Documentação completa

- **IPTU_Gerador_Documentacao_Tecnica_v3.docx** — descrição de cada arquivo, API, banco, motor PDF, interface
- **IPTU_Gerador_Guia_Implantacao_v3.docx** — passo a passo de instalação, produção, HTTPS, backup e resolução de problemas
