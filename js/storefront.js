document.addEventListener("DOMContentLoaded", () => {
  const categoriesTrack = document.getElementById("categories-track");
  const productsTrack = document.getElementById("home-products");
  const heroTrack = document.getElementById("hero-track");
  const scrollAmount = (track) => Math.max(260, Math.round(track.clientWidth * 0.75));

  document.querySelectorAll(".carousel-arrow").forEach((button) => {
    button.addEventListener("click", () => {
      const direction = button.classList.contains("next") ? 1 : -1;
      const target = button.dataset.target;

      if (target === "hero" && heroTrack) {
        heroTrack.classList.toggle("reverse-layout");
        return;
      }

      const track = target === "categories" ? categoriesTrack : productsTrack;

      if (!track) {
        return;
      }

      track.scrollBy({ left: direction * scrollAmount(track), behavior: "smooth" });
    });
  });

  const megaItem = document.querySelector(".mega-item");
  const megaTrigger = document.querySelector(".mega-trigger");

  if (megaItem && megaTrigger) {
    megaTrigger.addEventListener("click", () => {
      megaItem.classList.toggle("is-open");
    });

    document.addEventListener("click", (event) => {
      if (!megaItem.contains(event.target)) {
        megaItem.classList.remove("is-open");
      }
    });
  }
});
