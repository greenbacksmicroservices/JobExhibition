(() => {
  const cards = document.querySelectorAll('[data-rating-card]');
  if (!cards.length) return;

  const responses = {
    1: 'Oh no! 😟 We will try to improve.',
    2: 'It was okay, but we can do better. 🙂',
    3: "Thanks! We're glad you liked it. 😊",
    4: 'Great! Thank you so much. ✨',
    5: 'Awesome! You made our day! 😍',
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
          messageEl.textContent = responses[value] || 'Thanks for your feedback!';
        }
        if (submitBtn) {
          submitBtn.classList.remove('is-hidden');
        }
      });
    });
  });
})();
