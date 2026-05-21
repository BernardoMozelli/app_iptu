import Swal from 'sweetalert2';

// Instância base com tema da Prefeitura
const swal = Swal.mixin({
  confirmButtonColor: '#0052A3',
  cancelButtonColor:  '#888',
  focusConfirm: false,
  customClass: { popup: 'swal-iptu' },
});

export const alertSucesso = (titulo, texto) =>
  swal.fire({ icon: 'success', title: titulo, text: texto });

export const alertErro = (titulo, texto) =>
  swal.fire({ icon: 'error', title: titulo, text: texto });

export const alertAviso = (titulo, texto) =>
  swal.fire({ icon: 'warning', title: titulo, text: texto });

export const confirmar = (titulo, texto, btnConfirmar = 'Confirmar') =>
  swal.fire({
    icon: 'question',
    title: titulo,
    text: texto,
    showCancelButton: true,
    confirmButtonText: btnConfirmar,
    cancelButtonText: 'Cancelar',
  });

export const confirmarExcluir = (titulo, texto) =>
  swal.fire({
    icon: 'warning',
    title: titulo,
    text: texto,
    showCancelButton: true,
    confirmButtonText: 'Sim, excluir',
    confirmButtonColor: '#C0392B',
    cancelButtonText: 'Cancelar',
  });

export const confirmarPurgar = (anoAnterior) =>
  swal.fire({
    icon: 'warning',
    title: `Apagar guias de ${anoAnterior}?`,
    html: `Você está gerando IPTUs para um novo ano.<br><br>
      As guias geradas em <strong>${anoAnterior}</strong> serão <strong>excluídas permanentemente</strong> 
      do servidor para liberar espaço.<br><br>
      <small style="color:#888">Certifique-se de ter feito download de tudo que precisava.</small>`,
    showCancelButton: true,
    confirmButtonText: `Sim, apagar guias de ${anoAnterior}`,
    confirmButtonColor: '#C0392B',
    cancelButtonText: 'Cancelar geração',
  });

export default swal;
