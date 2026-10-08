(() => {
  const root = document.documentElement;
  root.classList.add("js");

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const curtain = document.querySelector(".transition-curtain");
  const siteHeader = document.querySelector(".site-header");
  const menuToggle = document.querySelector(".menu-toggle");
  let transitionTimer;

  const closeMenu = () => {
    if (!siteHeader || !menuToggle) return;

    siteHeader.classList.remove("menu-open");
    menuToggle.setAttribute("aria-expanded", "false");
  };

  if (menuToggle && siteHeader) {
    menuToggle.addEventListener("click", () => {
      const isOpen = siteHeader.classList.toggle("menu-open");
      menuToggle.setAttribute("aria-expanded", String(isOpen));
    });

    document.addEventListener("click", (event) => {
      if (siteHeader.classList.contains("menu-open") && !siteHeader.contains(event.target)) {
        closeMenu();
      }
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeMenu();
    });
  }

  const revealItems = document.querySelectorAll("[data-reveal]");

  if ("IntersectionObserver" in window && !reducedMotion.matches) {
    const revealObserver = new IntersectionObserver(
      (entries, observer) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;

          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -7%" },
    );

    revealItems.forEach((item, index) => {
      item.style.setProperty("--reveal-delay", `${Math.min(index % 4, 3) * 70}ms`);
      revealObserver.observe(item);
    });
  } else {
    revealItems.forEach((item) => item.classList.add("is-visible"));
  }

  const scrollToTarget = (target, hash) => {
    const offset = target.id === "top" ? 0 : 12;
    const top = Math.max(0, target.getBoundingClientRect().top + window.scrollY - offset);

    window.scrollTo({ top, behavior: "auto" });
    window.history.pushState({}, "", hash);
  };

  document.querySelectorAll('a[data-transition-link][href^="#"]').forEach((link) => {
    link.addEventListener("click", (event) => {
      const hash = link.getAttribute("href");
      const target = hash ? document.querySelector(hash) : null;

      if (!target) return;

      event.preventDefault();
      closeMenu();
      window.clearTimeout(transitionTimer);

      if (reducedMotion.matches || !curtain) {
        scrollToTarget(target, hash);
        return;
      }

      curtain.classList.remove("is-clearing");
      curtain.classList.add("is-active");

      transitionTimer = window.setTimeout(() => {
        scrollToTarget(target, hash);
        curtain.classList.add("is-clearing");

        transitionTimer = window.setTimeout(() => {
          curtain.classList.remove("is-active", "is-clearing");
        }, 430);
      }, 220);
    });
  });

  const copyStatus = document.querySelector("#copy-status");

  const copyText = async (text) => {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return;
    }

    const helper = document.createElement("textarea");
    helper.value = text;
    helper.setAttribute("readonly", "");
    helper.style.position = "fixed";
    helper.style.opacity = "0";
    document.body.appendChild(helper);
    helper.select();
    document.execCommand("copy");
    helper.remove();
  };

  document.querySelectorAll("[data-copy]").forEach((button) => {
    button.addEventListener("click", async () => {
      const source = document.getElementById(button.dataset.copy);
      if (!source) return;

      try {
        await copyText(source.textContent.trim());
        button.textContent = "Copied";
        if (copyStatus) copyStatus.textContent = "Command copied to your clipboard.";

        window.setTimeout(() => {
          button.textContent = "Copy";
          if (copyStatus) copyStatus.textContent = "";
        }, 2200);
      } catch {
        if (copyStatus) copyStatus.textContent = "Copy failed. Select the command manually.";
      }
    });
  });
})();
