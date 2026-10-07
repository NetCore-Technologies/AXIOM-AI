(() => {
  document.querySelectorAll(".reveal").forEach((element) => {
    element.classList.add("is-visible");
  });

  document.querySelectorAll("[data-count]").forEach((element) => {
    element.textContent = element.dataset.count || "0";
  });
})();
