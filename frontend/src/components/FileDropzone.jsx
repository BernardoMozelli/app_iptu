import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { FileText, X, Upload } from 'lucide-react';

export default function FileDropzone({ files, onChange, label, accept, multiple = true }) {
  const onDrop = useCallback((accepted) => {
    if (multiple) onChange(prev => [...prev, ...accepted]);
    else onChange(accepted.slice(0, 1));
  }, [multiple, onChange]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: accept || { 'text/plain': ['.txt'] },
    multiple,
  });

  const remove = (i) => onChange(prev => prev.filter((_, idx) => idx !== i));

  return (
    <div>
      <div
        {...getRootProps()}
        style={{
          border: `2px dashed ${isDragActive ? '#7BC043' : '#B0BAC8'}`,
          borderRadius: 10,
          padding: '28px 20px',
          textAlign: 'center',
          cursor: 'pointer',
          background: isDragActive ? '#F0FAF0' : '#FAFBFC',
          transition: 'all .2s',
        }}
      >
        <input {...getInputProps()} />
        <Upload size={28} color="#0052A3" style={{ margin: '0 auto 8px' }} />
        <p style={{ color: '#445566', fontWeight: 600, fontSize: '0.9rem' }}>
          {isDragActive ? 'Solte aqui!' : label || 'Arraste ou clique para selecionar'}
        </p>
        <p style={{ color: '#888', fontSize: '0.78rem', marginTop: 4 }}>
          {multiple ? 'Múltiplos arquivos .txt' : 'Imagem JPG ou PNG'}
        </p>
      </div>

      {files.length > 0 && (
        <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 6 }}>
          {files.map((f, i) => (
            <div key={i} style={{
              display: 'flex', alignItems: 'center', gap: 10,
              background: '#F5F7FA', border: '1px solid #E2E6ED',
              borderRadius: 8, padding: '8px 12px',
            }}>
              <FileText size={14} color="#0052A3" />
              <span style={{ flex: 1, fontSize: '0.85rem', color: '#333', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {f.name}
              </span>
              <span style={{ fontSize: '0.75rem', color: '#888', whiteSpace: 'nowrap' }}>
                {(f.size / 1024).toFixed(1)} KB
              </span>
              <button onClick={() => remove(i)} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2 }}>
                <X size={14} color="#C0392B" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
