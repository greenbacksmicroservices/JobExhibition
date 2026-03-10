document.addEventListener('DOMContentLoaded', () => {
  const toggles = document.querySelectorAll('[data-password-toggle]');
  if (!toggles.length) return;

  toggles.forEach((toggle) => {
    const targetId = toggle.getAttribute('data-password-toggle');
    if (!targetId) return;
    const input = document.getElementById(targetId);
    if (!input) return;

    const updateLabel = () => {
      toggle.textContent = input.type === 'password' ? 'Show' : 'Hide';
    };

    toggle.addEventListener('click', () => {
      input.type = input.type === 'password' ? 'text' : 'password';
      updateLabel();
    });

    updateLabel();
  });
});
