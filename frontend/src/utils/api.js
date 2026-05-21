import axios from 'axios';

const api = axios.create({ baseURL: '/api' });

export const gerarIPTU        = (formData, onUploadProgress) =>
  api.post('/gerar', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress,
    timeout: 0,
  });

export const getProgresso      = (jobId)  => api.get(`/progresso/${jobId}`);
export const cancelarJob       = (jobId)  => api.post(`/cancelar/${jobId}`);
export const excluirPDF        = (caminho) => api.delete('/pdf', { params: { caminho } });
export const downloadTodosUrl  = (jobId)  => `/api/download-todos/${jobId}`;
export const downloadSessaoUrl = (id)     => `/api/download-sessao/${id}`;
export const getPdfsSessao     = (id)     => api.get(`/pdfs-sessao/${id}`);
export const getHistorico      = (limite = 100) => api.get('/historico', { params: { limite } });
export const getDetalhe        = (id)     => api.get(`/historico/${id}`);
export const getStats          = ()       => api.get('/estatisticas');
export const limparHistorico   = ()       => api.delete('/historico');
export const purgarAnoAnterior = (ano)    => api.delete('/purgar-ano-anterior', { params: { ano } });

export default api;
