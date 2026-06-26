document.addEventListener('DOMContentLoaded', function () {

  const testimonialsSwiper = new Swiper('.testimonials-swiper', {

    slidesPerView: 1,
    centeredSlides: true,
    loop: true,
    speed: 700,
    grabCursor: true,
    initialSlide: 2,
    spaceBetween: 16,

    pagination: {
      el: '.testi-pagination',
      clickable: true,
    },

    navigation: {
      prevEl: '.testi-prev',
      nextEl: '.testi-next',
    },

    autoplay: {
      delay: 4500,
      disableOnInteraction: false,
      pauseOnMouseEnter: true,
    },

    keyboard: {
      enabled: true,
      onlyInViewport: true,
    },

    a11y: {
      enabled: true,
      prevSlideMessage: 'Previous testimonial',
      nextSlideMessage: 'Next testimonial',
    },

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
