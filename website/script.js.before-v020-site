const observer = new IntersectionObserver(
  entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add("visible");
        observer.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.12 }
);

document
  .querySelectorAll(".reveal")
  .forEach(element => observer.observe(element));

const graph = document.querySelector(".graph-line");

if (graph) {
  let pulse = 0;

  setInterval(() => {
    pulse += 0.02;
    graph.style.opacity = String(
      0.82 + Math.sin(pulse) * 0.14
    );
  }, 80);
}
