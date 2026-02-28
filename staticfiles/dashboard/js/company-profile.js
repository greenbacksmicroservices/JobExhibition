document.addEventListener('DOMContentLoaded', () => {
  const editBtn = document.getElementById('companyInfoEditBtn');
  const cancelBtn = document.getElementById('companyInfoCancelBtn');
  const viewBlock = document.getElementById('companyInfoView');
  const formBlock = document.getElementById('companyInfoForm');

  if (editBtn && viewBlock && formBlock) {
    editBtn.addEventListener('click', () => {
      viewBlock.style.display = 'none';
      formBlock.style.display = 'block';
    });
  }

  if (cancelBtn && viewBlock && formBlock) {
    cancelBtn.addEventListener('click', () => {
      formBlock.style.display = 'none';
      viewBlock.style.display = 'grid';
    });
  }

  const uploadBtn = document.getElementById('logoUploadBtn');
  const logoInput = document.getElementById('logoInput');
  const logoForm = document.getElementById('logoUploadForm');
  const logoPreview = document.querySelector('.logo-preview');

  if (uploadBtn && logoInput) {
    uploadBtn.addEventListener('click', () => {
      logoInput.click();
    });
  }

  if (logoInput && logoForm) {
    logoInput.addEventListener('change', () => {
      const file = logoInput.files && logoInput.files[0];
      if (!file) return;

      if (logoPreview) {
        const url = URL.createObjectURL(file);
        let img = logoPreview.querySelector('img');
        const fallback = logoPreview.querySelector('span');
        if (!img) {
          img = document.createElement('img');
          logoPreview.innerHTML = '';
          logoPreview.appendChild(img);
        }
        img.src = url;
        if (fallback) {
          fallback.remove();
        }
      }

      logoForm.submit();
    });
  }

  const kycGrid = document.getElementById('kycUploadGrid');
  const addKycBtn = document.getElementById('addKycDocumentBtn');
  const kycTemplate = document.getElementById('kycDocTemplate');
  const kycTableBody = document.getElementById('kycDocsTableBody');
  let kycCounter = 0;

  const escapeHtml = (value) => {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  };

  const ensureEmptyRow = () => {
    if (!kycTableBody) return;
    const hasRows = kycTableBody.querySelectorAll('tr').length > 0;
    if (hasRows) return;
    const emptyRow = document.createElement('tr');
    emptyRow.className = 'kyc-empty-row';
    emptyRow.dataset.kycEmpty = 'true';
    emptyRow.innerHTML = '<td colspan="4" class="muted" style="text-align:center; padding: 16px;">No documents uploaded yet.</td>';
    kycTableBody.appendChild(emptyRow);
  };

  const removeEmptyRow = () => {
    if (!kycTableBody) return;
    const emptyRow = kycTableBody.querySelector('[data-kyc-empty]');
    if (emptyRow) {
      emptyRow.remove();
    }
  };

  const upsertKycRow = (card) => {
    if (!kycTableBody || !card) return;
    const fileInput = card.querySelector('.kyc-file-input');
    if (!fileInput) return;
    const file = fileInput.files && fileInput.files[0];
    const docId = fileInput.dataset.docId || `kyc-${++kycCounter}`;
    fileInput.dataset.docId = docId;

    if (!file) {
      const row = kycTableBody.querySelector(`tr[data-doc-id="${docId}"]`);
      if (row) {
        row.remove();
      }
      ensureEmptyRow();
      return;
    }

    removeEmptyRow();
    let row = kycTableBody.querySelector(`tr[data-doc-id="${docId}"]`);
    if (!row) {
      row = document.createElement('tr');
      row.dataset.docId = docId;
      kycTableBody.appendChild(row);
    }

    const titleValue = card.querySelector('input[name="kyc_document_title"]')?.value || file.name;
    const typeLabel = card.querySelector('select[name="kyc_document_type"] option:checked')?.textContent || 'Document';
    const fileUrl = URL.createObjectURL(file);

    row.innerHTML = `
      <td><strong>${escapeHtml(titleValue)}</strong></td>
      <td>${escapeHtml(typeLabel)}</td>
      <td>Pending upload</td>
      <td>
        <div class="table-actions">
          <a class="action-btn" href="${fileUrl}" target="_blank" rel="noopener">View</a>
          <a class="action-btn" href="${fileUrl}" download>Download</a>
        </div>
      </td>
    `;

    row.querySelectorAll('a').forEach((link) => {
      link.addEventListener('click', () => {
        setTimeout(() => URL.revokeObjectURL(fileUrl), 10000);
      });
    });
  };

  const attachKycCardHandlers = (card) => {
    if (!card) return;
    const fileInput = card.querySelector('.kyc-file-input');
    const removeBtn = card.querySelector('[data-remove-kyc]');
    const titleInput = card.querySelector('input[name="kyc_document_title"]');
    const typeSelect = card.querySelector('select[name="kyc_document_type"]');

    if (fileInput) {
      fileInput.dataset.docId = fileInput.dataset.docId || `kyc-${++kycCounter}`;
      fileInput.addEventListener('change', () => upsertKycRow(card));
    }

    const updateHandler = () => {
      const file = fileInput && fileInput.files && fileInput.files[0];
      if (file) {
        upsertKycRow(card);
      }
    };

    if (titleInput) {
      titleInput.addEventListener('input', updateHandler);
    }

    if (typeSelect) {
      typeSelect.addEventListener('change', updateHandler);
    }

    if (removeBtn) {
      removeBtn.addEventListener('click', () => {
        const docId = fileInput && fileInput.dataset.docId;
        if (docId && kycTableBody) {
          const row = kycTableBody.querySelector(`tr[data-doc-id="${docId}"]`);
          if (row) {
            row.remove();
          }
        }
        card.remove();
        const remainingCards = kycGrid ? kycGrid.querySelectorAll('[data-kyc-card]').length : 0;
        if (!remainingCards) {
          ensureEmptyRow();
        }
        syncRemoveButtons();
      });
    }
  };

  const syncRemoveButtons = () => {
    if (!kycGrid) return;
    const cards = kycGrid.querySelectorAll('[data-kyc-card]');
    cards.forEach((card) => {
      const removeBtn = card.querySelector('[data-remove-kyc]');
      if (!removeBtn) return;
      const isPrimary = !!card.querySelector('input[type="file"][name="registration_document"]');
      if (isPrimary) {
        removeBtn.style.display = 'none';
        return;
      }
      removeBtn.style.display = cards.length > 1 ? 'inline-flex' : 'none';
    });
  };

  if (kycGrid) {
    kycGrid.querySelectorAll('[data-kyc-card]').forEach((card) => {
      attachKycCardHandlers(card);
    });
    syncRemoveButtons();
  }

  if (addKycBtn && kycGrid && kycTemplate) {
    addKycBtn.addEventListener('click', () => {
      const fragment = kycTemplate.content.cloneNode(true);
      const card = fragment.querySelector('[data-kyc-card]');
      if (card) {
        attachKycCardHandlers(card);
      }
      kycGrid.appendChild(fragment);
      syncRemoveButtons();
    });
  }
});
