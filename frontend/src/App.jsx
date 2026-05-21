import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Toaster } from 'react-hot-toast';
import { FileText, Image, Play } from 'lucide-react';

import Header from './components/Header';
import Card, { CardHeader } from './components/Card';
import FileDropzone from './components/FileDropzone';
import ProgressPanel from './components/ProgressPanel';
import ResultsPanel from './components/ResultsPanel';
import HistoricoPanel from './components/HistoricoPanel';
import { gerarIPTU, getProgresso, cancelarJob, getHistorico, purgarAnoAnterior } from './utils/api';
import { alertErro, confirmarPurgar } from './utils/swal';

const POLL_MS = 800;

// Extrai o ano IPTU de uma lista de sessões do histórico
function anoMaxHistorico(sessoes) {
  let max = 0;
  for (const s of sessoes) {
    const data = s.iniciado_em || '';
    try {
      const ano = parseInt(data.split('/')[2]?.split(' ')[0], 10);
      if (ano > max) max = ano;
    } catch { /* */ }
  }
  return max;
}

export default function App() {
  const [ano, setAno]             = useState(new Date().getFullYear());
  const [arquivosTxt, setArquivosTxt]   = useState([]);
  const [arquivoVerso, setArquivoVerso] = useState([]);
  const [jobId, setJobId]         = useState(null);
  const [progresso, setProgresso] = useState(null);
  const [enviando, setEnviando]   = useState(false);
  const [histKey, setHistKey]     = useState(0); // força reload do histórico
  const pollRef = useRef(null);

  const iniciarPoll = useCallback((id) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const r = await getProgresso(id);
        setProgresso(r.data);
        if (['concluido', 'cancelado', 'erro'].includes(r.data.status)) {
          clearInterval(pollRef.current);
          pollRef.current = null;
          setHistKey(k => k + 1); // atualiza histórico ao terminar
        }
      } catch { /* sem-op */ }
    }, POLL_MS);
  }, []);

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

  // Verifica se há sessões de ano anterior antes de iniciar geração
  const verificarPurge = async () => {
    const anoAtual = new Date().getFullYear();
    try {
      const r = await getHistorico(9999);
      const sessoes = r.data || [];
      const anoMax  = anoMaxHistorico(sessoes);
      if (anoMax > 0 && anoMax < anoAtual) {
        const conf = await confirmarPurgar(anoMax);
        if (!conf.isConfirmed) return false; // usuário cancelou a geração
        await purgarAnoAnterior(anoAtual);
        setHistKey(k => k + 1);
      }
    } catch { /* não bloqueia */ }
    return true;
  };

  const handleGerar = async () => {
    if (arquivosTxt.length === 0) {
      alertErro('Nenhum arquivo', 'Selecione ao menos um arquivo .txt.');
      return;
    }

    // Verificar purge de ano anterior
    const podeGerar = await verificarPurge();
    if (!podeGerar) return;

    setEnviando(true);
    setProgresso(null);

    const form = new FormData();
    arquivosTxt.forEach(f => form.append('arquivos', f));
    if (arquivoVerso[0]) form.append('verso', arquivoVerso[0]);

    try {
      const r = await gerarIPTU(form, (ev) => {
        if (ev.total) {
          const pct = (ev.loaded / ev.total) * 100;
          setProgresso({ status: 'enviando', percent: pct, log: [`📤 Enviando arquivos… ${Math.round(pct)}%`], pdfs: [] });
        }
      });
      const id = r.data.job_id;
      setJobId(id);
      iniciarPoll(id);
    } catch (err) {
      alertErro('Erro ao iniciar', err.response?.data?.detail || err.message);
    } finally {
      setEnviando(false);
    }
  };

  const handleCancelar = async () => {
    if (!jobId) return;
    try { await cancelarJob(jobId); } catch { /* sem-op */ }
  };

  const emProcesso = progresso && ['processando', 'enviando', 'cancelando'].includes(progresso.status);

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: '#F0F2F5' }}>
      <Toaster position="top-right" toastOptions={{ duration: 3500 }} />
      <Header ano={ano} />

      <main style={{ flex: 1, padding: '28px 16px', maxWidth: 900, width: '100%', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 20 }}>

        {/* Arquivos TXT */}
        <Card>
          <CardHeader icon={FileText} iconColor="#0052A3" title="Arquivos de Dados (.txt)" subtitle="Exportados do ERP Supernova" />
          <div style={{ padding: 20 }}>
            <FileDropzone files={arquivosTxt} onChange={setArquivosTxt}
              label="Arraste os arquivos .txt aqui ou clique para selecionar" multiple />
          </div>
        </Card>

        {/* Imagem do verso */}
        <Card>
          <CardHeader icon={Image} iconColor="#7BC043" title="Imagem do Verso (opcional)" subtitle="Substitui a imagem padrão do carnê" />
          <div style={{ padding: 20, display: 'flex', gap: 20, alignItems: 'flex-start', flexWrap: 'wrap' }}>
            <div style={{ flex: '1 1 260px' }}>
              <FileDropzone files={arquivoVerso} onChange={setArquivoVerso}
                label="Arraste uma imagem JPG/PNG ou clique"
                accept={{ 'image/jpeg': ['.jpg', '.jpeg'], 'image/png': ['.png'] }}
                multiple={false} />
            </div>
            <div style={{ flex: '0 0 200px' }}>
              <p style={{ fontSize: '0.75rem', color: '#888', marginBottom: 8 }}>Imagem padrão atual:</p>
              <img src="/static/img/iptu-verso.jpg" alt="Verso padrão"
                style={{ width: '100%', borderRadius: 8, border: '1px solid #DDE1E7', objectFit: 'cover' }} />
            </div>
          </div>
        </Card>

        {/* Botão Gerar */}
        <button
          onClick={handleGerar}
          disabled={enviando || emProcesso || arquivosTxt.length === 0}
          style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
            background: enviando || emProcesso || arquivosTxt.length === 0 ? '#B0BAC8' : '#0052A3',
            color: '#fff', border: 'none', borderRadius: 10,
            padding: '14px 28px', fontSize: '1rem', fontWeight: 700,
            cursor: enviando || emProcesso || arquivosTxt.length === 0 ? 'not-allowed' : 'pointer',
            transition: 'background .2s',
          }}
        >
          <Play size={18} />
          {enviando ? 'Enviando…' : emProcesso ? 'Gerando…' : `Gerar PDFs (${arquivosTxt.length} arquivo${arquivosTxt.length !== 1 ? 's' : ''})`}
        </button>

        {progresso && <ProgressPanel progresso={progresso} onCancelar={handleCancelar} />}
        {progresso?.status === 'concluido' && <ResultsPanel progresso={progresso} jobId={jobId} />}

        <HistoricoPanel recarregarKey={histKey} />
      </main>

      <footer style={{ marginTop: 40 }}>
        {/* Barra tricolor */}
        <div style={{
          height: 3,
          background: 'linear-gradient(to right, #0052A3 0%, #0052A3 33.33%, #7BC043 33.33%, #7BC043 66.66%, #F39200 66.66%, #F39200 100%)',
        }} />
        {/* Corpo azul escuro */}
        <div style={{
          background: '#003D7A',
          padding: '12px 20px',
          display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
        }}>
          <p style={{ margin: 0, fontSize: '0.81rem', color: '#fff', fontWeight: 500, letterSpacing: '0.3px', textAlign: 'center' }}>
            Prefeitura Municipal de Santa Luzia - MG | www.santaluzia.mg.gov.br | IPTU {ano}
          </p>
          <p style={{ margin: 0, fontSize: '0.81rem', color: '#fff', fontWeight: 600, letterSpacing: '0.3px', textAlign: 'center' }}>
            Desenvolvido pela Secretaria Municipal de Planejamento, Ciência, Tecnologia e Inovação
          </p>
        </div>
      </footer>
    </div>
  );
}
