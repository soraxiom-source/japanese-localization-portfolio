const catalog = {};

function interpolate(message, variables = {}) {
  return message.replace(/\{([a-zA-Z][\w]*)\}/g, (match, name) =>
    Object.prototype.hasOwnProperty.call(variables, name) ? variables[name] : match
  );
}

function lookup(object, path) {
  return path.split(".").reduce((value, segment) => value?.[segment], object);
}

async function loadLocale(locale) {
  if (!catalog[locale]) {
    const response = await fetch(`locales/${locale}.json`);
    if (!response.ok) throw new Error(`Could not load locale: ${locale}`);
    catalog[locale] = await response.json();
  }
  return catalog[locale];
}

async function setLocale(locale) {
  const messages = await loadLocale(locale);
  document.documentElement.lang = locale;
  document.title = messages.meta.title;

  document.querySelectorAll("[data-i18n]").forEach((element) => {
    const key = element.dataset.i18n;
    const value = lookup(messages, key);
    if (typeof value !== "string") {
      console.warn(`Missing translation: ${locale}.${key}`);
      return;
    }
    const variables = element.dataset.i18nVars ? JSON.parse(element.dataset.i18nVars) : {};
    element.textContent = interpolate(value, variables);
  });

  document.querySelectorAll("[data-locale]").forEach((button) => {
    const active = button.dataset.locale === locale;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  localStorage.setItem("demo-locale", locale);
}

document.querySelectorAll("[data-locale]").forEach((button) => {
  button.addEventListener("click", () => setLocale(button.dataset.locale));
});

setLocale(localStorage.getItem("demo-locale") || "en").catch((error) => {
  console.error(error);
  document.body.dataset.localeError = "true";
});
