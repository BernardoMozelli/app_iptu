import React from 'react';

export default function Card({ children, style = {} }) {
  return (
    <div style={{
      background: '#fff',
      border: '1px solid #DDE1E7',
      borderRadius: 12,
      overflow: 'hidden',
      boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
      ...style,
    }}>
      {children}
    </div>
  );
}

export function CardHeader({ icon: Icon, iconColor = '#0052A3', title, subtitle, trailing }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12,
      padding: '16px 20px', borderBottom: '1px solid #EEF0F4',
      background: '#FAFBFC',
    }}>
      {Icon && <Icon size={18} color={iconColor} />}
      <div style={{ flex: 1 }}>
        <div style={{ fontWeight: 700, color: '#1A2A3A', fontSize: '0.95rem' }}>{title}</div>
        {subtitle && <div style={{ fontSize: '0.75rem', color: '#888', marginTop: 2 }}>{subtitle}</div>}
      </div>
      {trailing}
    </div>
  );
}
