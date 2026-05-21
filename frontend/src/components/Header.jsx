import React from 'react';

export default function Header({ ano }) {
  return (
    <header style={{ background: '#fff', borderBottom: '1px solid #DDE1E7', flexShrink: 0 }}>
      {/* Barra tricolor */}
      <div style={{
        height: 6,
        background: 'linear-gradient(to right, #0052A3 0%, #0052A3 33.33%, #7BC043 33.33%, #7BC043 66.66%, #F39200 66.66%, #F39200 100%)',
      }} />
      <div style={{ padding: '12px 32px', display: 'flex', alignItems: 'center', gap: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 18 }}>
          <img src="/static/img/logo_prefeitura.png" alt="Logo Prefeitura" style={{ height: 68, objectFit: 'contain', maxWidth: 300 }} />
          <div style={{ width: 1, height: 44, background: '#DDE1E7' }} />
          <div>
            <h1 style={{ fontSize: '1.18rem', fontWeight: 700, color: '#0052A3', letterSpacing: '0.01em', lineHeight: 1.2 }}>
              Gerador de Carnês de IPTU
            </h1>
            <p style={{ fontSize: '0.78rem', color: '#888', marginTop: 3 }}>
              Secretaria de Planejamento, Ciência, Tecnologia e Inovação
            </p>
          </div>
        </div>
        <div style={{ marginLeft: 'auto' }}>
          <span style={{
            background: '#0052A3', color: '#fff', fontSize: '0.7rem', fontWeight: 700,
            padding: '4px 12px', borderRadius: 20, letterSpacing: '0.05em',
          }}>
            IPTU {ano}
          </span>
        </div>
      </div>
    </header>
  );
}
