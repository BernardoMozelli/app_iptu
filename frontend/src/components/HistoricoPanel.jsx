import React, { useState, useEffect } from 'react';
import { History, RefreshCw, Trash2, FileText, Download, PackageOpen, ChevronDown, ChevronUp } from 'lucide-react';
import Card, { CardHeader } from './Card';
import { getHistorico, getStats, getPdfsSessao, downloadSessaoUrl, limparHistorico } from '../utils/api';
import { confirmarExcluir, alertSucesso, alertErro } from '../utils/swal';

const STATUS_BADGE = {
  concluido:    { bg: '#E8F5E9', color: '#2E7D32', label: 'Concluído' },
  cancelado:    { bg: '#FFF3E0', color: '#E65100', label: 'Cancelado' },
  erro:         { bg: '#FDECEA', color: '#C0392B', label: 'Erro' },
  em_andamento: { bg: '#E3F2FD', color: '#0052A3', label: 'Em andamento' },
};

function SessaoRow({ s, onAtualizar }) {
  const [aberta, setAberta]   = useState(false);
  const [pdfs, setPdfs]       = useState([]);
  const [carregando, setCarregando] = useState(false);

  const badge   = STATUS_BADGE[s.status] || STATUS_BADGE.em_andamento;
  const detalhe = s.status === 'concluido'
    ? `${(s.total_registros || 0).toLocaleString('pt-BR')} registros · ${s.num_pdfs || 0} PDF(s)`
    : (s.erro_msg || badge.label || '').slice(0, 70);

  const toggleAbrir = async () => {
    if (!aberta && pdfs.length === 0 && s.status === 'concluido') {
      setCarregando(true);
      try {
        const r = await getPdfsSessao(s.id);
        setPdfs(r.data);
      } catch { /* sem-op */ }
      setCarregando(false);
    }
    setAberta(v => !v);
  };

  return (
    <div style={{ border: '1px solid #E8ECF2', borderRadius: 8, overflow: 'hidden' }}>
      {/* Linha principal clicável */}
      <div
        onClick={s.status === 'concluido' ? toggleAbrir : undefined}
        style={{
          display: 'flex', alignItems: 'center', gap: 12,
          background: aberta ? '#F0F5FF' : '#F9FAFB',
          padding: '10px 14px',
          cursor: s.status === 'concluido' ? 'pointer' : 'default',
          userSelect: 'none',
        }}
      >
        <span style={{
          background: badge.bg, color: badge.color,
          fontSize: '0.72rem', fontWeight: 700,
          padding: '2px 9px', borderRadius: 20, whiteSpace: 'nowrap',
        }}>
          {badge.label}
        </span>

        <div style={{ flex: 1, overflow: 'hidden' }}>
          <div style={{ fontWeight: 600, fontSize: '0.85rem', color: '#1A2A3A', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {s.arquivos_entrada || '—'}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#888', marginTop: 2 }}>{detalhe}</div>
        </div>

        <span style={{ fontSize: '0.75rem', color: '#AAA', whiteSpace: 'nowrap' }}>
          {s.iniciado_em}
        </span>

        {s.status === 'concluido' && (
          <span style={{ color: '#0052A3', marginLeft: 4 }}>
            {aberta ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </span>
        )}
      </div>

      {/* Painel expansível com PDFs */}
      {aberta && (
        <div style={{ background: '#FAFBFF', borderTop: '1px solid #E8ECF2', padding: '10px 14px' }}>
          {carregando ? (
            <p style={{ color: '#888', fontSize: '0.82rem' }}>Carregando PDFs…</p>
          ) : pdfs.length === 0 ? (
            <p style={{ color: '#BBB', fontSize: '0.82rem' }}>
              Nenhum PDF disponível — podem ter sido excluídos ou o servidor foi reiniciado.
            </p>
          ) : (
            <>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {pdfs.map((pdf, i) => (
                  <div key={i} style={{
                    display: 'flex', alignItems: 'center', gap: 10,
                    background: '#fff', border: '1px solid #E2E6ED',
                    borderRadius: 6, padding: '7px 12px',
                  }}>
                    {/* Ícone PDF vermelho */}
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" fill="#C0392B" stroke="#C0392B" strokeWidth="0"/>
                      <polyline points="14 2 14 8 20 8" fill="#E87070" stroke="#fff" strokeWidth="1.5"/>
                      <text x="5" y="18" fontSize="6" fontWeight="bold" fill="white" fontFamily="Arial">PDF</text>
                    </svg>
                    <span style={{ flex: 1, fontSize: '0.82rem', color: '#333', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {pdf.nome}
                    </span>
                    <span style={{ fontSize: '0.72rem', color: '#888', whiteSpace: 'nowrap' }}>
                      {pdf.tamanho_mb?.toFixed(1)} MB
                    </span>
                    <a
                      href={pdf.url}
                      download={pdf.nome}
                      style={{
                        display: 'flex', alignItems: 'center', gap: 4,
                        background: '#0052A3', color: '#fff', textDecoration: 'none',
                        padding: '4px 10px', borderRadius: 6, fontSize: '0.75rem', fontWeight: 600,
                      }}
                    >
                      <Download size={11} /> Baixar
                    </a>
                  </div>
                ))}
              </div>

              {/* Baixar todos da sessão */}
              <div style={{ marginTop: 10, display: 'flex', justifyContent: 'flex-end' }}>
                <a
                  href={downloadSessaoUrl(s.id)}
                  download
                  style={{
                    display: 'inline-flex', alignItems: 'center', gap: 6,
                    background: '#7BC043', color: '#fff', textDecoration: 'none',
                    padding: '6px 14px', borderRadius: 7, fontSize: '0.8rem', fontWeight: 700,
                  }}
                >
                  <PackageOpen size={13} /> Baixar Todos (.zip)
                </a>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default function HistoricoPanel({ recarregarKey }) {
  const [sessoes, setSessoes] = useState([]);
  const [stats, setStats]     = useState(null);
  const [loading, setLoading] = useState(false);

  const carregar = async () => {
    setLoading(true);
    try {
      const [h, s] = await Promise.all([getHistorico(100), getStats()]);
      setSessoes(h.data);
      setStats(s.data);
    } catch { /* sem-op */ }
    setLoading(false);
  };

  useEffect(() => { carregar(); }, [recarregarKey]);

  const handleLimpar = async () => {
    const r = await confirmarExcluir(
      'Limpar todo o histórico?',
      'Isso apagará todas as sessões e os PDFs gerados permanentemente. Esta ação não pode ser desfeita.'
    );
    if (!r.isConfirmed) return;
    try {
      await limparHistorico();
      await alertSucesso('Histórico limpo', 'Todas as sessões e PDFs foram removidos.');
      carregar();
    } catch {
      alertErro('Erro', 'Não foi possível limpar o histórico.');
    }
  };

  return (
    <Card>
      <CardHeader
        icon={History}
        iconColor="#0052A3"
        title="Histórico de Gerações"
        subtitle={stats ? `${stats.total_sessoes} sessão(ões) registrada(s)` : ''}
        trailing={
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              onClick={carregar}
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                background: 'none', border: '1px solid #DDE1E7',
                borderRadius: 8, padding: '6px 12px', cursor: 'pointer',
                color: '#445566', fontSize: '0.8rem',
              }}
            >
              <RefreshCw size={13} /> Atualizar
            </button>
            {sessoes.length > 0 && (
              <button
                onClick={handleLimpar}
                style={{
                  display: 'flex', alignItems: 'center', gap: 6,
                  background: 'none', border: '1px solid #C0392B',
                  borderRadius: 8, padding: '6px 12px', cursor: 'pointer',
                  color: '#C0392B', fontSize: '0.8rem',
                }}
              >
                <Trash2 size={13} /> Limpar
              </button>
            )}
          </div>
        }
      />

      {/* Stats bar */}
      {stats && stats.total_sessoes > 0 && (
        <div style={{
          background: '#F5F7FA', borderBottom: '1px solid #E8ECF2',
          padding: '10px 20px', fontSize: '0.8rem', color: '#445566', fontWeight: 500,
        }}>
          📊 {stats.concluidas} concluídas &nbsp;|&nbsp;
          {(stats.total_registros || 0).toLocaleString('pt-BR')} registros &nbsp;|&nbsp;
          {stats.total_pdfs} PDFs gerados
        </div>
      )}

      <div style={{ padding: 20 }}>
        {loading ? (
          <p style={{ color: '#888', fontSize: '0.85rem' }}>Carregando…</p>
        ) : sessoes.length === 0 ? (
          <p style={{ color: '#BBB', fontSize: '0.85rem', textAlign: 'center' }}>
            Nenhuma geração realizada ainda.
          </p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {sessoes.map(s => <SessaoRow key={s.id} s={s} onAtualizar={carregar} />)}
          </div>
        )}
      </div>
    </Card>
  );
}
