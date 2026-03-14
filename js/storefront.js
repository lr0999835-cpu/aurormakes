document.addEventListener("DOMContentLoaded", () => {
  const categoriesTrack = document.getElementById("categories-track");
  const productsTrack = document.getElementById("home-products");
  const heroTrack = document.getElementById("hero-track");
  const heroSlides = heroTrack ? Array.from(heroTrack.querySelectorAll("[data-slide]")) : [];
  const megaItems = Array.from(document.querySelectorAll(".mega-item"));
  const mobileNav = document.getElementById("mobile-nav-drawer");
  const openMobileNavBtn = document.querySelector("[data-mobile-nav-toggle]");
  const closeMobileNavBtn = document.querySelector("[data-mobile-nav-close]");

  const scrollAmount = (track) => Math.max(260, Math.round(track.clientWidth * 0.78));

  const setHeroSlide = (nextIndex) => {
    if (!heroSlides.length) {
      return;
    }

    const normalizedIndex = (nextIndex + heroSlides.length) % heroSlides.length;
    heroSlides.forEach((slide, index) => {
      slide.classList.toggle("active", index === normalizedIndex);
    });

    heroTrack.dataset.activeSlide = String(normalizedIndex);
  };

  document.querySelectorAll(".carousel-arrow").forEach((button) => {
    button.addEventListener("click", () => {
      const direction = button.classList.contains("next") ? 1 : -1;
      const target = button.dataset.target;

      if (target === "hero" && heroTrack) {
        const activeIndex = Number(heroTrack.dataset.activeSlide || 0);
        setHeroSlide(activeIndex + direction);
        return;
      }

      const track = target === "categories" ? categoriesTrack : productsTrack;

      if (!track) {
        return;
      }

      track.scrollBy({ left: direction * scrollAmount(track), behavior: "smooth" });
    });
  });

  setHeroSlide(0);

  megaItems.forEach((item) => {
    const trigger = item.querySelector(".mega-trigger");

    if (!trigger) {
      return;
    }

    trigger.addEventListener("click", () => {
      const shouldOpen = !item.classList.contains("is-open");

      megaItems.forEach((currentItem) => {
        currentItem.classList.remove("is-open");
        const currentTrigger = currentItem.querySelector(".mega-trigger");

        if (currentTrigger) {
          currentTrigger.setAttribute("aria-expanded", "false");
        }
      });

      if (shouldOpen) {
        item.classList.add("is-open");
        trigger.setAttribute("aria-expanded", "true");
      }
    });
  });

  document.addEventListener("click", (event) => {
    megaItems.forEach((item) => {
      if (item.contains(event.target)) {
        return;
      }

      item.classList.remove("is-open");
      const trigger = item.querySelector(".mega-trigger");

      if (trigger) {
        trigger.setAttribute("aria-expanded", "false");
      }
    });
  });

  const closeMobileNav = () => {
    if (!mobileNav || !openMobileNavBtn) {
      return;
    }

    mobileNav.classList.remove("is-open");
    mobileNav.setAttribute("aria-hidden", "true");
    openMobileNavBtn.setAttribute("aria-expanded", "false");
    document.body.style.overflow = "";
  };

  const openMobileNav = () => {
    if (!mobileNav || !openMobileNavBtn) {
      return;
    }

    mobileNav.classList.add("is-open");
    mobileNav.setAttribute("aria-hidden", "false");
    openMobileNavBtn.setAttribute("aria-expanded", "true");
    document.body.style.overflow = "hidden";
  };

  if (openMobileNavBtn && mobileNav) {
    openMobileNavBtn.addEventListener("click", () => {
      const isOpen = mobileNav.classList.contains("is-open");

      if (isOpen) {
        closeMobileNav();
        return;
      }

      openMobileNav();
    });
  }

  if (closeMobileNavBtn) {
    closeMobileNavBtn.addEventListener("click", closeMobileNav);
  }

  if (mobileNav) {
    mobileNav.addEventListener("click", (event) => {
      if (event.target === mobileNav) {
        closeMobileNav();
      }
    });
  }

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeMobileNav();
    }
  });
});
