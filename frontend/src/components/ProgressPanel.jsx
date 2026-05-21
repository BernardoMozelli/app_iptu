import React, { useEffect, useRef } from 'react';
import { Terminal, XCircle } from 'lucide-react';
import Card, { CardHeader } from './Card';

export default function ProgressPanel({ progresso, onCancelar }) {
  const logRef = useRef(null);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [progresso?.log]);

  if (!progresso) return null;

  const { status, percent, log = [] } = progresso;
  const ativo = status === 'processando' || status === 'cancelando';

  const corBarra = status === 'concluido' ? '#7BC043'
    : status === 'cancelado' ? '#F39200'
    : status === 'erro' ? '#C0392B'
    : '#0052A3';

  return (
    <Card>
      <CardHeader
        icon={Terminal}
        iconColor="#0052A3"
        title="Progresso da Geração"
        subtitle={status === 'processando' ? 'Gerando PDFs…' : status === 'concluido' ? 'Concluído!' : status}
        trailing={
          ativo && (
            <button
              onClick={onCancelar}
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                background: 'none', border: '2px solid #C0392B',
                borderRadius: 8, padding: '6px 14px', cursor: 'pointer',
                color: '#C0392B', fontWeight: 600, fontSize: '0.82rem',
              }}
            >
              <XCircle size={14} /> Cancelar
            </button>
          )
        }
      />

      <div style={{ padding: 20 }}>
        {/* Barra de progresso */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
            <span style={{ fontSize: '0.8rem', color: '#555', fontWeight: 600 }}>
              {status === 'processando' ? 'Processando…' : status === 'concluido' ? '✅ Concluído' : status}
            </span>
            <span style={{ fontSize: '0.8rem', color: '#888' }}>{Math.round(percent || 0)}%</span>
          </div>
          <div style={{ height: 10, background: '#EEF0F4', borderRadius: 99, overflow: 'hidden' }}>
            <div style={{
              height: '100%', background: corBarra, borderRadius: 99,
              width: `${percent || 0}%`,
              transition: 'width .4s ease',
            }} />
          </div>
        </div>

        {/* Log terminal */}
        <div
          ref={logRef}
          style={{
            background: '#1A2233', borderRadius: 8, padding: '12px 16px',
            height: 220, overflowY: 'auto', fontFamily: 'monospace',
            fontSize: '0.78rem', lineHeight: 1.7, color: '#C8D8E8',
          }}
        >
          {log.length === 0
            ? <span style={{ color: '#556677' }}>Aguardando início…</span>
            : log.map((l, i) => (
                <div key={i} style={{
                  color: l.startsWith('❌') ? '#FF6B6B'
                    : l.startsWith('✅') ? '#7BC043'
                    : l.startsWith('⚠') ? '#F39200'
                    : '#C8D8E8',
                }}>{l}</div>
              ))
          }
        </div>
      </div>
    </Card>
  );
}
