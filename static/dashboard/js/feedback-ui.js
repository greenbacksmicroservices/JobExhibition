(() => {
  const cards = document.querySelectorAll('[data-rating-card]');
  if (!cards.length) return;

  const responses = {
    1: 'Oh no! Hum behtar karenge.',
    2: 'Theek hai, aur improve karenge.',
    3: 'Shukriya! Accha laga.',
    4: 'Bohat badhiya! Thank you.',
    5: 'Gazab! Aapka feedback best hai.',
  };

  cards.forEach((card) => {
    const messageEl = card.querySelector('[data-rating-message]');
    const inputWrap = card.querySelector('[data-rating-input]');
    if (!inputWrap) return;

    const form = card.closest('form');
    const submitBtn = form ? form.querySelector('[data-rating-submit]') : null;

    inputWrap.querySelectorAll('input[type="radio"]').forEach((input) => {
      input.addEventListener('change', (event) => {
        const value = Number(event.target.value || 0);
        if (messageEl) {
          messageEl.textContent = responses[value] || 'Shukriya!';
        }
        if (submitBtn) {
          submitBtn.classList.remove('is-hidden');
        }
      });
    });
  });
})();
