document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('form[data-suggestions-endpoint]');
  if (!form) {
    return;
  }

  const endpoint = form.dataset.suggestionsEndpoint || '';
  if (!endpoint) {
    return;
  }

  const inputs = Array.from(form.querySelectorAll('input[data-suggest-field][list]'));
  if (!inputs.length) {
    return;
  }

  const timers = new WeakMap();
  const cache = new Map();
  const resolveCountryContext = () => {
    const countryInput = form.querySelector('[name="country"], [name="nationality"]');
    return (countryInput?.value || '').trim();
  };

  const updateDatalist = (input, values) => {
    const listId = input.getAttribute('list');
    if (!listId) return;
    const datalist = document.getElementById(listId);
    if (!datalist) return;
    datalist.innerHTML = values
      .slice(0, 12)
      .map((value) => `<option value="${String(value).replace(/"/g, '&quot;')}"></option>`)
      .join('');
  };

  const fetchSuggestions = async (input) => {
    const field = (input.dataset.suggestField || '').trim();
    const query = (input.value || '').trim();
    const country = resolveCountryContext();
    if (!field) {
      updateDatalist(input, []);
      return;
    }

    const cacheKey = `${field}|${query.toLowerCase()}|${country.toLowerCase()}`;
    if (cache.has(cacheKey)) {
      updateDatalist(input, cache.get(cacheKey));
      return;
    }

    const params = new URLSearchParams({ field, q: query });
    if (country) {
      params.set('country', country);
    }
    try {
      const response = await fetch(`${endpoint}?${params.toString()}`, {
        credentials: 'same-origin',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
        },
      });
      if (!response.ok) {
        updateDatalist(input, []);
        return;
      }
      const payload = await response.json();
      const suggestions = Array.isArray(payload.suggestions) ? payload.suggestions : [];
      cache.set(cacheKey, suggestions);
      updateDatalist(input, suggestions);
    } catch {
      updateDatalist(input, []);
    }
  };

  inputs.forEach((input) => {
    input.addEventListener('input', () => {
      const activeTimer = timers.get(input);
      if (activeTimer) {
        clearTimeout(activeTimer);
      }
      const timer = setTimeout(() => fetchSuggestions(input), 150);
      timers.set(input, timer);
    });
    input.addEventListener('focus', () => fetchSuggestions(input));
  });
});
