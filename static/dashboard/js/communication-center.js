(() => {
  const smsTextarea = document.querySelector('.sms-textarea');
  const charCount = document.querySelector('.char-count');
  if (smsTextarea && charCount) {
    const updateCount = () => {
      const count = smsTextarea.value.length;
      charCount.textContent = `${count} / 160`;
    };
    smsTextarea.addEventListener('input', updateCount);
    updateCount();
  }

  const previewBtn = document.getElementById('emailPreviewBtn');
  const subjectInput = document.getElementById('bulkEmailSubject');
  const editor = document.getElementById('bulkEmailEditor');
  const previewSubject = document.getElementById('emailPreviewSubject');
  const previewBody = document.getElementById('emailPreviewBody');

  const updatePreview = () => {
    if (!previewSubject || !previewBody) return;
    const subject = subjectInput && subjectInput.value ? subjectInput.value : 'No subject';
    const bodyText = editor ? editor.innerText.trim() : '';
    previewSubject.textContent = subject;
    previewBody.textContent = bodyText || 'No content yet.';
  };

  if (previewBtn) {
    previewBtn.addEventListener('click', updatePreview);
  }
})();
