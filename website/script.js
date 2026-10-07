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
