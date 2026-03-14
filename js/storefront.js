document.addEventListener("DOMContentLoaded", () => {
  const heroBannerData = [
    {
      key: "esfoliantes",
      image: "images/banners/esfoliantes-poran.svg",
      alt: "Banner Esfoliantes Porán: O segredo para uma pele sedosa e macia.",
      title: "Conheça os Esfoliantes Porán",
      subtitle: "O segredo para uma pele sedosa e macia.",
      button_text: "Saiba mais",
      button_url: "produtos.html?categoria=esfoliantes"
    },
    {
      key: "body-splash",
      image: "images/banners/body-splash-rose-essence.svg",
      alt: "Banner Body Splash Rose Essence com chamada para ótima fixação.",
      title: "Body Splash Rose Essence",
      subtitle: "Fragrância encantadora com ótima fixação.",
      button_text: "Ótima fixação",
      button_url: "produtos.html?categoria=body-splash"
    },
    {
      key: "choco-fun",
      image: "images/banners/choco-fun-batom-matte.svg",
      alt: "Banner Choco Fun destacando batom efeito matte.",
      title: "Batom efeito matte",
      subtitle: "Coleção Choco Fun Fenzza.",
      button_text: "Clique e confira",
      button_url: "produtos.html?categoria=batom"
    }
  ];

  const categoriesTrack = document.getElementById("categories-track");
  const productsTrack = document.getElementById("home-products");
  const heroTrack = document.getElementById("hero-track");
  const heroDots = document.getElementById("hero-dots");
  const heroSlideTemplate = document.getElementById("hero-slide-template");
  const heroSlides = [];
  let heroAutoPlayInterval;
  const megaItems = Array.from(document.querySelectorAll(".mega-item"));
  const mobileNav = document.getElementById("mobile-nav-drawer");
  const openMobileNavBtn = document.querySelector("[data-mobile-nav-toggle]");
  const closeMobileNavBtn = document.querySelector("[data-mobile-nav-close]");

  const scrollAmount = (track) => Math.max(260, Math.round(track.clientWidth * 0.78));

  const buildHeroSlides = () => {
    if (!heroTrack || !heroSlideTemplate) {
      return;
    }

    const fragment = document.createDocumentFragment();

    heroBannerData.forEach((banner, index) => {
      const slideNode = heroSlideTemplate.content.cloneNode(true);
      const slide = slideNode.querySelector("[data-slide]");
      const image = slideNode.querySelector(".hero-image");
      const title = slideNode.querySelector("[data-hero-title]");
      const subtitle = slideNode.querySelector("[data-hero-subtitle]");
      const cta = slideNode.querySelector("[data-hero-cta]");

      slide.dataset.bannerKey = banner.key;
      image.src = banner.image;
      image.alt = banner.alt;
      image.loading = index === 0 ? "eager" : "lazy";
      title.textContent = banner.title;
      subtitle.textContent = banner.subtitle;
      cta.textContent = banner.button_text;
      cta.href = banner.button_url;
      cta.setAttribute("aria-label", `${banner.button_text}: ${banner.title}`);

      fragment.appendChild(slideNode);
    });

    heroTrack.innerHTML = "";
    heroTrack.appendChild(fragment);
    heroSlides.push(...heroTrack.querySelectorAll("[data-slide]"));
  };

  const buildHeroDots = () => {
    if (!heroDots) {
      return;
    }

    heroDots.innerHTML = "";

    heroBannerData.forEach((banner, index) => {
      const dot = document.createElement("button");
      dot.type = "button";
      dot.className = "hero-dot";
      dot.setAttribute("aria-label", `Ir para banner ${index + 1}: ${banner.title}`);
      dot.dataset.heroDot = String(index);
      heroDots.appendChild(dot);
    });
  };

  const setHeroSlide = (nextIndex) => {
    if (!heroSlides.length) {
      return;
    }

    const normalizedIndex = (nextIndex + heroSlides.length) % heroSlides.length;
    heroSlides.forEach((slide, index) => {
      slide.classList.toggle("active", index === normalizedIndex);
    });

    if (heroDots) {
      Array.from(heroDots.querySelectorAll("[data-hero-dot]")).forEach((dot, dotIndex) => {
        dot.classList.toggle("active", dotIndex === normalizedIndex);
        dot.setAttribute("aria-current", dotIndex === normalizedIndex ? "true" : "false");
      });
    }

    heroTrack.dataset.activeSlide = String(normalizedIndex);
  };

  const startHeroAutoplay = () => {
    if (!heroTrack || heroSlides.length < 2 || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      return;
    }

    clearInterval(heroAutoPlayInterval);
    heroAutoPlayInterval = window.setInterval(() => {
      const activeIndex = Number(heroTrack.dataset.activeSlide || 0);
      setHeroSlide(activeIndex + 1);
    }, 7000);
  };

  const stopHeroAutoplay = () => {
    clearInterval(heroAutoPlayInterval);
  };

  buildHeroSlides();
  buildHeroDots();

  document.querySelectorAll(".carousel-arrow").forEach((button) => {
    button.addEventListener("click", () => {
      const direction = button.classList.contains("next") ? 1 : -1;
      const target = button.dataset.target;

      if (target === "hero" && heroTrack) {
        const activeIndex = Number(heroTrack.dataset.activeSlide || 0);
        setHeroSlide(activeIndex + direction);
        startHeroAutoplay();
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

  if (heroDots) {
    heroDots.addEventListener("click", (event) => {
      const target = event.target;

      if (!(target instanceof HTMLButtonElement) || !target.dataset.heroDot) {
        return;
      }

      setHeroSlide(Number(target.dataset.heroDot));
      startHeroAutoplay();
    });
  }

  if (heroTrack) {
    heroTrack.addEventListener("mouseenter", stopHeroAutoplay);
    heroTrack.addEventListener("mouseleave", startHeroAutoplay);
    heroTrack.addEventListener("focusin", stopHeroAutoplay);
    heroTrack.addEventListener("focusout", startHeroAutoplay);

    let touchStartX = 0;

    heroTrack.addEventListener("touchstart", (event) => {
      touchStartX = event.changedTouches[0].clientX;
    }, { passive: true });

    heroTrack.addEventListener("touchend", (event) => {
      const touchEndX = event.changedTouches[0].clientX;
      const travel = touchStartX - touchEndX;

      if (Math.abs(travel) < 45) {
        return;
      }

      const activeIndex = Number(heroTrack.dataset.activeSlide || 0);
      setHeroSlide(activeIndex + (travel > 0 ? 1 : -1));
      startHeroAutoplay();
    }, { passive: true });
  }

  document.addEventListener("keydown", (event) => {
    if (!heroTrack || (event.key !== "ArrowLeft" && event.key !== "ArrowRight")) {
      return;
    }

    const activeIndex = Number(heroTrack.dataset.activeSlide || 0);
    setHeroSlide(activeIndex + (event.key === "ArrowRight" ? 1 : -1));
    startHeroAutoplay();
  });

  startHeroAutoplay();

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
