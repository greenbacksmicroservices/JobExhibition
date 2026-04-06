document.addEventListener('DOMContentLoaded', () => {
  const forms = Array.from(document.querySelectorAll('form[data-registration-otp-url]'));
  if (!forms.length) {
    return;
  }

  const emailPattern = /[^@]+@[^@]+\.[^@]+/;
  const phonePattern = /^\+?\d{10,15}$/;

  const getCsrfToken = (form) =>
    form.querySelector('input[name="csrfmiddlewaretoken"]')?.value || '';

  const ensureStatusNode = (input) => {
    if (!input) {
      return null;
    }

    const existing = input.parentElement?.querySelector(`[data-otp-status-for="${input.name}"]`);
    if (existing) {
      return existing;
    }

    const statusNode = document.createElement('div');
    statusNode.className = 'otp-inline-status';
    statusNode.setAttribute('data-otp-status-for', input.name);
    statusNode.setAttribute('aria-live', 'polite');
    input.parentElement?.insertBefore(statusNode, input);
    return statusNode;
  };

  const paintStatus = (node, kind, message) => {
    if (!node) {
      return;
    }
    node.classList.remove('is-success', 'is-error', 'is-info');
    if (!message) {
      node.textContent = '';
      return;
    }
    if (kind === 'success') {
      node.classList.add('is-success');
    } else if (kind === 'error') {
      node.classList.add('is-error');
    } else {
      node.classList.add('is-info');
    }
    node.textContent = message;
  };

  const requestOtp = async (form, button) => {
    const endpoint = form.dataset.registrationOtpUrl;
    if (!endpoint) {
      return;
    }

    const channel = (button.dataset.otpSendChannel || '').trim().toLowerCase();
    const targetName = (button.dataset.otpTarget || '').trim();
    const otpInput = targetName ? form.querySelector(`input[name="${targetName}"]`) : null;
    const flow = otpInput?.dataset?.otpFlow || '';
    const email = (form.querySelector('input[name="email"]')?.value || '').trim();
    const phone = (form.querySelector('input[name="phone"]')?.value || '').trim();
    const statusNode = ensureStatusNode(otpInput);

    if (!flow || !channel || !otpInput) {
      paintStatus(statusNode, 'error', 'OTP setup incomplete. Please refresh page.');
      return;
    }

    if (channel === 'email') {
      if (!email) {
        paintStatus(statusNode, 'error', 'Please enter email before requesting OTP.');
        return;
      }
      if (!emailPattern.test(email)) {
        paintStatus(statusNode, 'error', 'Enter a valid email address.');
        return;
      }
    }

    if (channel === 'sms') {
      if (!phone) {
        paintStatus(statusNode, 'error', 'Please enter mobile number before requesting OTP.');
        return;
      }
      if (!phonePattern.test(phone)) {
        paintStatus(statusNode, 'error', 'Enter a valid mobile number (10 to 15 digits).');
        return;
      }
    }

    const csrfToken = getCsrfToken(form);
    const originalLabel = button.textContent;
    button.disabled = true;
    button.textContent = 'Sending...';
    paintStatus(statusNode, 'info', 'Sending OTP...');

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
          'X-CSRFToken': csrfToken,
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: new URLSearchParams({
          flow,
          channel,
          email,
          phone,
        }).toString(),
      });

      const payload = await response.json().catch(() => ({}));
      if (!response.ok || !payload.success) {
        const errorMessage = payload.error || 'Unable to send OTP right now. Please try again.';
        paintStatus(statusNode, 'error', errorMessage);
        return;
      }

      const successMessage = payload.message || 'OTP sent successfully.';
      paintStatus(statusNode, 'success', successMessage);
      otpInput.focus();
    } catch {
      paintStatus(statusNode, 'error', 'Network error. Please try again.');
    } finally {
      button.disabled = false;
      button.textContent = originalLabel;
    }
  };

  forms.forEach((form) => {
    const otpButtons = Array.from(form.querySelectorAll('[data-otp-send-button]'));
    otpButtons.forEach((button) => {
      button.addEventListener('click', (event) => {
        event.preventDefault();
        requestOtp(form, button);
      });
    });
  });
});
