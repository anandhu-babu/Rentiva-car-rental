document.addEventListener('DOMContentLoaded', function () {

  const testimonialsSwiper = new Swiper('.testimonials-swiper', {

    /* Core layout — Swiper controls slide widths via slidesPerView */
    slidesPerView: 1,
    centeredSlides: true,
    loop: true,
    speed: 700,
    grabCursor: true,
    initialSlide: 2,
    spaceBetween: 16,

    /* Pagination dots */
    pagination: {
      el: '.testi-pagination',
      clickable: true,
    },

    /* Prev / Next arrows */
    navigation: {
      prevEl: '.testi-prev',
      nextEl: '.testi-next',
    },

    /* Autoplay */
    autoplay: {
      delay: 4500,
      disableOnInteraction: false,
      pauseOnMouseEnter: true,
    },

    /* Keyboard navigation (arrow keys when section is in view) */
    keyboard: {
      enabled: true,
      onlyInViewport: true,
    },

    /* Accessibility */
    a11y: {
      enabled: true,
      prevSlideMessage: 'Previous testimonial',
      nextSlideMessage: 'Next testimonial',
    },

    /* Responsive breakpoints:
       Mobile  (<640px)  → 1 card
       Tablet  (640px+)  → 2 cards
       Desktop (1024px+) → 3 cards, centered active */
    breakpoints: {
      640: {
        slidesPerView: 2,
        centeredSlides: false,
        spaceBetween: 22,
      },
      1024: {
        slidesPerView: 3,
        centeredSlides: true,
        spaceBetween: 28,
      },
    },
  });

});
