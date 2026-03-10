document.addEventListener('DOMContentLoaded', () => {
  const isOtpInput = (input) => {
    if (!input || input.tagName !== 'INPUT') return false;
    const type = (input.getAttribute('type') || '').toLowerCase();
    if (type && !['text', 'tel', 'number', 'password'].includes(type)) return false;
    const name = (input.getAttribute('name') || '').toLowerCase();
    const placeholder = (input.getAttribute('placeholder') || '').toLowerCase();
    return name.includes('otp') || placeholder.includes('otp');
  };

  const otpInputs = Array.from(document.querySelectorAll('input')).filter(isOtpInput);
  if (!otpInputs.length) return;

  const debounceTimers = new WeakMap();

  const getCsrfToken = (form) =>
    form?.querySelector('input[name="csrfmiddlewaretoken"]')?.value || '';

  const updateState = (input, verified) => {
    if (typeof verified === 'boolean') {
      input.classList.toggle('otp-verified', verified);
      input.dataset.otpVerified = verified ? '1' : '0';
      return;
    }
    const raw = (input.value || '').trim();
    const digits = raw.replace(/\D/g, '');
    const isVerified = digits.length >= 6;
    input.classList.toggle('otp-verified', isVerified);
  };

  const verifyWithServer = async (input) => {
    const verifyUrl = input.dataset.otpVerifyUrl;
    const flow = input.dataset.otpFlow;
    const channel = input.dataset.otpChannel;
    if (!verifyUrl || !flow || !channel) {
      updateState(input);
      return;
    }

    const raw = (input.value || '').trim();
    const digits = raw.replace(/\D/g, '');
    if (digits.length < 6) {
      updateState(input, false);
      return;
    }

    const form = input.closest('form');
    const email = form?.querySelector('input[name="email"]')?.value || '';
    const phone = form?.querySelector('input[name="phone"]')?.value || '';
    const csrfToken = getCsrfToken(form);

    try {
      const response = await fetch(verifyUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
          'X-CSRFToken': csrfToken,
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: new URLSearchParams({
          flow,
          channel,
          otp: digits,
          email,
          phone,
        }).toString(),
      });
      const payload = await response.json();
      updateState(input, Boolean(payload.verified));
    } catch {
      updateState(input, false);
    }
  };

  otpInputs.forEach((input) => {
    updateState(input);
    input.addEventListener('input', () => {
      const existing = debounceTimers.get(input);
      if (existing) clearTimeout(existing);
      const timer = setTimeout(() => verifyWithServer(input), 300);
      debounceTimers.set(input, timer);
    });
    input.addEventListener('blur', () => verifyWithServer(input));
  });
});
