/**
 * BuszApp · Modal
 *
 * Helpers para abrir/fechar modais padronizados (.bz-modal-overlay/.bz-modal-box)
 * e construir modais de confirmação ad-hoc.
 *
 * Uso (modal declarado no HTML):
 *   <div id="meuModal" class="bz-modal-overlay hidden">
 *     <div class="bz-modal-box">
 *       <h3 class="bz-modal-title">Título</h3>
 *       <p class="bz-modal-desc">Descrição</p>
 *       …conteúdo…
 *       <div class="bz-modal-actions">
 *         <button class="bz-btn bz-btn-ghost" onclick="Modal.close('meuModal')">Cancelar</button>
 *         <button class="bz-btn bz-btn-primary">Confirmar</button>
 *       </div>
 *     </div>
 *   </div>
 *   <script> Modal.open('meuModal') </script>
 *
 * Uso (confirm ad-hoc):
 *   Modal.confirm({
 *     title: 'Excluir motorista?',
 *     desc:  'Esta ação não pode ser desfeita.',
 *     confirmText: 'Excluir',
 *     confirmVariant: 'danger',
 *     onConfirm: () => deleteDriver(id),
 *   });
 */
(function () {
  const ACTIVE = new Set();   // ids de modais abertos
  let escListenerBound = false;

  function bindEscOnce() {
    if (escListenerBound) return;
    document.addEventListener('keydown', (e) => {
      if (e.key !== 'Escape' || ACTIVE.size === 0) return;
      const last = Array.from(ACTIVE).pop();
      Modal.close(last);
    });
    escListenerBound = true;
  }

  function bindOverlayClick(overlay) {
    if (overlay.dataset.bzBound === '1') return;
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) Modal.close(overlay.id);
    });
    overlay.dataset.bzBound = '1';
  }

  const Modal = {
    open(id) {
      const el = typeof id === 'string' ? document.getElementById(id) : id;
      if (!el) return;
      el.classList.remove('hidden');
      bindOverlayClick(el);
      bindEscOnce();
      ACTIVE.add(el.id);
      document.body.style.overflow = 'hidden';
    },

    close(id) {
      const el = typeof id === 'string' ? document.getElementById(id) : id;
      if (!el) return;
      el.classList.add('hidden');
      ACTIVE.delete(el.id);
      if (ACTIVE.size === 0) document.body.style.overflow = '';
    },

    /**
     * Modal.confirm({title, desc, confirmText, cancelText, confirmVariant, onConfirm, onCancel})
     * confirmVariant: 'primary' (default) | 'danger' | 'success'
     */
    confirm({
      title = 'Confirmar',
      desc  = '',
      confirmText = 'Confirmar',
      cancelText  = 'Cancelar',
      confirmVariant = 'primary',
      onConfirm,
      onCancel,
    } = {}) {
      const overlay = document.createElement('div');
      overlay.className = 'bz-modal-overlay';
      overlay.id = `bzConfirm-${Date.now()}-${Math.random().toString(36).slice(2,7)}`;

      const variant = ['primary', 'danger', 'success'].includes(confirmVariant) ? confirmVariant : 'primary';

      overlay.innerHTML = `
        <div class="bz-modal-box" style="max-width:420px">
          <h3 class="bz-modal-title">${escapeText(title)}</h3>
          ${desc ? `<p class="bz-modal-desc">${escapeText(desc)}</p>` : ''}
          <div class="bz-modal-actions">
            <button type="button" class="bz-btn bz-btn-ghost" data-bz-cancel>${escapeText(cancelText)}</button>
            <button type="button" class="bz-btn bz-btn-${variant}" data-bz-confirm>${escapeText(confirmText)}</button>
          </div>
        </div>
      `;

      document.body.appendChild(overlay);

      const cleanup = () => {
        Modal.close(overlay.id);
        // Remove do DOM no próximo tick para evitar piscar
        setTimeout(() => overlay.remove(), 0);
      };

      overlay.querySelector('[data-bz-cancel]').addEventListener('click', () => {
        cleanup();
        if (typeof onCancel === 'function') onCancel();
      });
      overlay.querySelector('[data-bz-confirm]').addEventListener('click', () => {
        cleanup();
        if (typeof onConfirm === 'function') onConfirm();
      });

      Modal.open(overlay);
      return overlay;
    },
  };

  function escapeText(str) {
    const d = document.createElement('div');
    d.textContent = str == null ? '' : String(str);
    return d.innerHTML;
  }

  window.Modal = Modal;
})();
