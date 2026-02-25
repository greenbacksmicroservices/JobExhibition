document.addEventListener('DOMContentLoaded', () => {
  const forms = document.querySelectorAll('[data-loading-form]');

  forms.forEach((form) => {
    form.addEventListener('submit', () => {
      const submitButtons = form.querySelectorAll('button[type="submit"]');
      submitButtons.forEach((btn) => {
        if (btn.classList.contains('btn-loading')) return;
        btn.classList.add('btn-loading');
        btn.setAttribute('disabled', 'disabled');
        const spinner = document.createElement('span');
        spinner.className = 'btn-spinner';
        spinner.setAttribute('aria-hidden', 'true');
        btn.appendChild(spinner);
      });
    });
  });

  const applyToggle = document.querySelector('[data-apply-toggle]');
  const applyPanel = document.querySelector('[data-apply-panel]');
  const applyCloseButtons = document.querySelectorAll('[data-apply-close]');
  const experienceSelect = document.querySelector('[data-experience-type]');
  const experienceDetails = document.querySelectorAll('[data-experience-details]');
  const tabButtons = document.querySelectorAll('[data-tab-target]');
  const tabSections = document.querySelectorAll('[data-tab-section]');

  const openApplyPanel = () => {
    if (!applyPanel) return;
    applyPanel.classList.add('is-open');
    if (applyToggle) {
      applyToggle.setAttribute('aria-expanded', 'true');
    }
    applyPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const closeApplyPanel = () => {
    if (!applyPanel) return;
    applyPanel.classList.remove('is-open');
    if (applyToggle) {
      applyToggle.setAttribute('aria-expanded', 'false');
    }
  };

  if (applyToggle && applyPanel) {
    applyToggle.addEventListener('click', openApplyPanel);
  }

  applyCloseButtons.forEach((button) => {
    button.addEventListener('click', closeApplyPanel);
  });

  const toggleExperienceFields = () => {
    if (!experienceSelect) return;
    const show = experienceSelect.value === 'Experienced';
    experienceDetails.forEach((field) => {
      field.style.display = show ? '' : 'none';
    });
  };

  if (experienceSelect) {
    toggleExperienceFields();
    experienceSelect.addEventListener('change', toggleExperienceFields);
  }

  const activateTab = (target) => {
    tabButtons.forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.tabTarget === target);
    });
    tabSections.forEach((section) => {
      section.classList.toggle('active', section.dataset.tabSection === target);
    });
  };

  if (tabButtons.length) {
    tabButtons.forEach((btn) => {
      btn.addEventListener('click', () => {
        activateTab(btn.dataset.tabTarget);
      });
    });
  }

  const repeatableSections = document.querySelectorAll('[data-repeatable]');
  repeatableSections.forEach((section) => {
    const list = section.querySelector('[data-repeatable-list]');
    const addBtn = section.querySelector('[data-add-row]');
    if (!list || !addBtn) return;
    addBtn.addEventListener('click', () => {
      const templateId = addBtn.dataset.templateId;
      const template = templateId ? document.getElementById(templateId) : null;
      if (template) {
        list.insertAdjacentHTML('beforeend', template.innerHTML.trim());
      }
    });
    list.addEventListener('click', (event) => {
      const removeBtn = event.target.closest('[data-remove-row]');
      if (!removeBtn) return;
      const row = removeBtn.closest('.repeatable-row');
      if (row) {
        row.remove();
      }
    });
  });
});
