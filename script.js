const header = document.querySelector("[data-site-header]");
const menuButton = document.querySelector(".menu-toggle");
const nav = document.querySelector(".site-nav");
const yearTarget = document.querySelector("[data-current-year]");
const contactForms = document.querySelectorAll(".contact-form");

if (yearTarget) {
  yearTarget.textContent = new Date().getFullYear();
}

function closeMenu() {
  if (!menuButton || !nav) {
    return;
  }

  menuButton.setAttribute("aria-expanded", "false");
  nav.classList.remove("is-open");
  document.body.classList.remove("menu-open");
}

function stampForm(form) {
  const timestamp = form.querySelector('input[name="timestamp"]');
  const page = form.querySelector('input[name="page"]');

  if (timestamp) {
    timestamp.value = new Date().toISOString();
  }

  if (page && !page.value) {
    page.value = window.location.pathname || "kontakt.html";
  }
}

if (menuButton && nav) {
  menuButton.addEventListener("click", () => {
    const isOpen = menuButton.getAttribute("aria-expanded") === "true";
    menuButton.setAttribute("aria-expanded", String(!isOpen));
    nav.classList.toggle("is-open", !isOpen);
    document.body.classList.toggle("menu-open", !isOpen);
  });

  nav.addEventListener("click", (event) => {
    const link = event.target.closest("a");

    if (link) {
      closeMenu();
    }
  });

  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeMenu();
    }
  });
}

contactForms.forEach((form) => {
  stampForm(form);
  form.addEventListener("submit", () => stampForm(form));
});

if (header) {
  window.addEventListener("hashchange", () => {
    let target = null;

    try {
      const targetId = decodeURIComponent(window.location.hash.slice(1));
      target = targetId ? document.getElementById(targetId) : null;
    } catch {
      target = null;
    }

    if (target) {
      target.setAttribute("tabindex", "-1");
      target.focus({ preventScroll: true });
    }
  });
}
