jQuery(document).ready(function ($) {


    // Page animation
    $(document).ready(function () {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                } else {
                    // Uncomment the line below if you want the animation to repeat when scrolling up
                    // entry.target.classList.remove('visible');
                }
            });
        }, {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px',
        });

        document.querySelectorAll('.animate').forEach(element => {
            observer.observe(element);
        });
    });
});

