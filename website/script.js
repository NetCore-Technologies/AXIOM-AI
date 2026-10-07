(() => {
  const revealItems = document.querySelectorAll(".reveal");

  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(
      (entries, obs) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue;
          entry.target.classList.add("is-visible");
          obs.unobserve(entry.target);
        }
      },
      {
        threshold: 0.12,
        rootMargin: "0px 0px -45px 0px",
      },
    );

    revealItems.forEach((item) => observer.observe(item));
  } else {
    revealItems.forEach((item) => item.classList.add("is-visible"));
  }

  document.querySelectorAll("[data-count]").forEach((node) => {
    const raw = Number(node.dataset.count);
    const decimals = raw % 1 ? 1 : 0;
    const duration = 1050;
    const start = performance.now();

    function tick(now) {
      const progress = Math.min(
        1,
        (now - start) / duration,
      );

      const eased =
        1 - Math.pow(1 - progress, 3);

      node.textContent = (raw * eased).toFixed(decimals);

      if (progress < 1) {
        requestAnimationFrame(tick);
      }
    }

    requestAnimationFrame(tick);
  });

  const consoleCard =
    document.querySelector(".hero-console");

  if (consoleCard && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    consoleCard.addEventListener("pointermove", (event) => {
      const rect = consoleCard.getBoundingClientRect();

      const x =
        ((event.clientX - rect.left) / rect.width) - .5;

      const y =
        ((event.clientY - rect.top) / rect.height) - .5;

      consoleCard.style.transform = `
        perspective(1600px)
        rotateY(${x * 3.5 - 2}deg)
        rotateX(${y * -2.5 + 1}deg)
        translateY(-3px)
      `;
    });

    consoleCard.addEventListener("pointerleave", () => {
      consoleCard.style.transform = `
        perspective(1600px)
        rotateY(-4deg)
        rotateX(2deg)
      `;
    });
  }
})();

/* AXIOM — resolve the newest published GitHub release.
   Prereleases are included and sorted by publication date. */

(async function loadLatestAxiomRelease() {
  const API =
    "https://api.github.com/repos/NetCore-Technologies/AXIOM-AI/releases?per_page=30";

  try {
    const response = await fetch(API, {
      headers: {
        Accept: "application/vnd.github+json"
      },
      cache: "no-store"
    });

    if (!response.ok) return;

    const releases = await response.json();

    const release = releases
      .filter((item) => !item.draft && item.published_at)
      .sort(
        (a, b) =>
          new Date(b.published_at).getTime() -
          new Date(a.published_at).getTime()
      )[0];

    if (!release) return;

    const tag = release.tag_name;

    document.querySelectorAll("[data-axiom-version]").forEach((el) => {
      el.textContent = tag;
    });

    document.querySelectorAll("a[data-axiom-release]").forEach((link) => {
      link.href = release.html_url;
    });

    document.querySelectorAll("[data-axiom-asset]").forEach((link) => {
      const suffix = link.getAttribute("data-axiom-asset");
      if (!suffix) return;

      const asset = release.assets.find(
        (item) => item.name === `AXIOM-${tag}-${suffix}`
      );

      if (asset) {
        link.href = asset.browser_download_url;
      }
    });
  } catch (error) {
    console.warn("AXIOM release lookup failed:", error);
  }
})();
