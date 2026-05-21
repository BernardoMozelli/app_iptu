import React from 'react';
import { Download, Trash2, CheckCircle, PackageOpen } from 'lucide-react';
import Card, { CardHeader } from './Card';
import { excluirPDF, downloadTodosUrl } from '../utils/api';
import { confirmarExcluir, alertErro } from '../utils/swal';

// Ícone PDF vermelho inline
const PdfIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ flexShrink: 0 }}>
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" fill="#C0392B"/>
    <polyline points="14 2 14 8 20 8" fill="#E87070" stroke="#fff" strokeWidth="1"/>
    <text x="5" y="18" fontSize="5.5" fontWeight="bold" fill="white" fontFamily="Arial">PDF</text>
  </svg>
);

export default function ResultsPanel({ progresso, jobId, onRefresh }) {
  if (!progresso || progresso.status !== 'concluido') return null;

  const { pdfs = [], total_registros = 0 } = progresso;

  const handleExcluir = async (pdf) => {
    const r = await confirmarExcluir('Excluir PDF?', `Deseja excluir ${pdf.nome}?`);
    if (!r.isConfirmed) return;
    try {
      await excluirPDF(pdf.caminho || pdf.url);
      onRefresh?.();
    } catch {
      alertErro('Erro', 'Não foi possível excluir o arquivo.');
    }
  };

  const BtnTodos = jobId && pdfs.length >= 1 ? (
    <a
      href={downloadTodosUrl(jobId)}
      download
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        background: '#7BC043', color: '#fff', textDecoration: 'none',
        padding: '7px 16px', borderRadius: 8, fontSize: '0.84rem', fontWeight: 700,
        whiteSpace: 'nowrap',
      }}
    >
      <PackageOpen size={15} /> Baixar Todos (.zip)
    </a>
  ) : null;

  return (
    <Card>
      <CardHeader
        icon={CheckCircle}
        iconColor="#7BC043"
        title="PDFs Gerados"
        subtitle={`${total_registros.toLocaleString('pt-BR')} registros · ${pdfs.length} arquivo(s)`}
        trailing={BtnTodos}
      />
      <div style={{ padding: 20 }}>
        {pdfs.length === 0 ? (
          <p style={{ color: '#888', fontSize: '0.85rem' }}>Nenhum PDF gerado.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {pdfs.map((pdf, i) => (
              <div key={i} style={{
                display: 'flex', alignItems: 'center', gap: 12,
                background: '#F9FAFB', border: '1px solid #E8ECF2',
                borderRadius: 8, padding: '10px 14px',
              }}>
                <PdfIcon />
                <div style={{ flex: 1, overflow: 'hidden' }}>
                  <div style={{ fontWeight: 600, fontSize: '0.88rem', color: '#1A2A3A', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {pdf.nome}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#888', marginTop: 2 }}>
                    {pdf.tamanho_mb?.toFixed(1)} MB
                  </div>
                </div>
                <a
                  href={pdf.url}
                  download={pdf.nome}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 6,
                    background: '#0052A3', color: '#fff', textDecoration: 'none',
                    padding: '6px 14px', borderRadius: 8, fontSize: '0.82rem', fontWeight: 600,
                  }}
                >
                  <Download size={13} /> Baixar
                </a>
                <button
                  onClick={() => handleExcluir(pdf)}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4 }}
                  title="Excluir"
                >
                  <Trash2 size={15} color="#C0392B" />
                </button>
              </div>
            ))}
            {BtnTodos && (
              <div style={{ marginTop: 8, display: 'flex', justifyContent: 'flex-end' }}>
                {BtnTodos}
              </div>
            )}
          </div>
        )}
      </div>
    </Card>
  );
}
