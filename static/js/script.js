/**
 * FoodExpress — Main JavaScript
 * Handles: navigation, flash messages, cart updates, toasts, form utilities
 */

document.addEventListener('DOMContentLoaded', function () {

    // ─── Mobile Navigation Toggle ────────────────────────────────────────────
    const navToggle = document.getElementById('navToggle');
    const navLinks  = document.getElementById('navLinks');

    if (navToggle && navLinks) {
        navToggle.addEventListener('click', function () {
            navLinks.classList.toggle('nav-open');
            navToggle.classList.toggle('active');
        });

        // Close menu when a link is clicked
        navLinks.querySelectorAll('a').forEach(function (link) {
            link.addEventListener('click', function () {
                navLinks.classList.remove('nav-open');
                navToggle.classList.remove('active');
            });
        });

        // Close menu on outside click
        document.addEventListener('click', function (e) {
            if (!navToggle.contains(e.target) && !navLinks.contains(e.target)) {
                navLinks.classList.remove('nav-open');
                navToggle.classList.remove('active');
            }
        });
    }

    // ─── Active Nav Link Highlighting ────────────────────────────────────────
    const currentPath = window.location.pathname;
    document.querySelectorAll('.nav-links a').forEach(function (link) {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });

    // ─── Auto-Dismiss Flash Messages ─────────────────────────────────────────
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(function (msg) {
        setTimeout(function () {
            msg.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            msg.style.opacity = '0';
            msg.style.transform = 'translateY(-10px)';
            setTimeout(function () {
                if (msg.parentNode) msg.parentNode.removeChild(msg);
            }, 500);
        }, 5000);
    });

    // ─── Cart Quantity Update (Cart Page) ────────────────────────────────────
    // updateCart is called inline from cart.html buttons
    window.updateCart = function (foodItemId, quantity) {
        fetch('/customer/cart/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ food_item_id: foodItemId, quantity: quantity })
        })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data.success) {
                // Reload page to recalculate totals server-side
                location.reload();
            } else {
                showToast('Failed to update cart.', 'error');
            }
        })
        .catch(function () {
            showToast('Network error. Please try again.', 'error');
        });
    };

    // ─── Clear Cart ───────────────────────────────────────────────────────────
    window.clearCart = function () {
        if (!confirm('Are you sure you want to clear your cart?')) return;
        fetch('/customer/cart/clear', { method: 'POST' })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data.success) {
                location.reload();
            }
        })
        .catch(function () {
            showToast('Failed to clear cart.', 'error');
        });
    };

    // ─── Toast Notifications ─────────────────────────────────────────────────
    window.showToast = function (message, type) {
        type = type || 'info';
        var iconMap = {
            success : 'fa-check-circle',
            error   : 'fa-exclamation-circle',
            warning : 'fa-exclamation-triangle',
            info    : 'fa-info-circle'
        };
        var toast = document.createElement('div');
        toast.className = 'toast toast-' + type;
        toast.innerHTML =
            '<i class="fas ' + (iconMap[type] || 'fa-info-circle') + '"></i> ' +
            message;
        document.body.appendChild(toast);

        // Trigger animation
        setTimeout(function () { toast.classList.add('show'); }, 10);

        // Auto-remove
        setTimeout(function () {
            toast.classList.remove('show');
            setTimeout(function () {
                if (toast.parentNode) toast.parentNode.removeChild(toast);
            }, 350);
        }, 3200);
    };

    // ─── Form Confirm Attribute ───────────────────────────────────────────────
    // Any form with data-confirm="message" will prompt the user before submit
    document.querySelectorAll('form[data-confirm]').forEach(function (form) {
        form.addEventListener('submit', function (e) {
            var msg = form.getAttribute('data-confirm') || 'Are you sure?';
            if (!confirm(msg)) {
                e.preventDefault();
            }
        });
    });

    // ─── Broken Image Fallbacks ───────────────────────────────────────────────
    document.querySelectorAll('img[onerror]').forEach(function (img) {
        // onerror is already set inline in templates; this handles lazy-loaded images
        img.addEventListener('error', function () {
            if (this.src.indexOf('placeholder') === -1) {
                if (this.classList.contains('item-thumb') ||
                    this.closest('.food-img') ||
                    this.closest('.cart-item-img')) {
                    this.src = '/static/images/food_placeholder.svg';
                } else {
                    this.src = '/static/images/restaurant_placeholder.svg';
                }
            }
        });
    });

    // ─── Toggle Password Visibility ──────────────────────────────────────────
    document.querySelectorAll('.toggle-password').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var target = document.getElementById(this.getAttribute('data-target'));
            if (!target) return;
            if (target.type === 'password') {
                target.type = 'text';
                this.innerHTML = '<i class="fas fa-eye-slash"></i>';
            } else {
                target.type = 'password';
                this.innerHTML = '<i class="fas fa-eye"></i>';
            }
        });
    });

    // ─── Nav Cart Count (keep in sync with session) ───────────────────────────
    // The server renders the cart count via session on page load.
    // This ensures the navCartCount element shows the right number after AJAX adds.
    var navCartCount = document.getElementById('navCartCount');
    if (navCartCount) {
        // If the element has a data-count attribute (set server-side), use it
        var dataCount = navCartCount.getAttribute('data-count');
        if (dataCount !== null) {
            navCartCount.textContent = dataCount;
        }
    }

    // ─── Auto-submit Filter Forms on Select Change ────────────────────────────
    document.querySelectorAll('select.auto-submit').forEach(function (sel) {
        sel.addEventListener('change', function () {
            this.closest('form').submit();
        });
    });

    // ─── Restaurant/Food Image Load Animation ─────────────────────────────────
    document.querySelectorAll('.restaurant-card img, .food-img img').forEach(function (img) {
        img.style.opacity = '0';
        img.style.transition = 'opacity 0.4s ease';
        if (img.complete) {
            img.style.opacity = '1';
        } else {
            img.addEventListener('load', function () {
                this.style.opacity = '1';
            });
        }
    });

    // ─── Table Row Highlight ──────────────────────────────────────────────────
    document.querySelectorAll('.data-table tbody tr').forEach(function (row) {
        row.addEventListener('mouseenter', function () {
            this.style.backgroundColor = 'rgba(255, 107, 0, 0.04)';
        });
        row.addEventListener('mouseleave', function () {
            this.style.backgroundColor = '';
        });
    });

    // ─── Smooth Scroll for Anchor Links ──────────────────────────────────────
    document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
        anchor.addEventListener('click', function (e) {
            var target = document.querySelector(this.getAttribute('href'));
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    // ─── Stats Counter Animation (index page) ────────────────────────────────
    function animateCounter(el) {
        var target = parseInt(el.textContent.replace(/\D/g, ''), 10);
        if (isNaN(target) || target === 0) return;
        var start    = 0;
        var duration = 1200;
        var step     = Math.ceil(target / (duration / 16));
        var timer = setInterval(function () {
            start += step;
            if (start >= target) {
                start = target;
                clearInterval(timer);
            }
            el.textContent = start + (el.textContent.includes('+') ? '+' : '');
        }, 16);
    }

    // Intersection Observer to trigger counter when in view
    var counterEls = document.querySelectorAll('.hero-stat strong');
    if (counterEls.length && 'IntersectionObserver' in window) {
        var observer = new IntersectionObserver(function (entries, obs) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    animateCounter(entry.target);
                    obs.unobserve(entry.target);
                }
            });
        }, { threshold: 0.5 });
        counterEls.forEach(function (el) { observer.observe(el); });
    }

    // ─── Flash Container: close button ───────────────────────────────────────
    document.querySelectorAll('.flash-close').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var msg = this.closest('.flash-message');
            if (msg) {
                msg.style.opacity = '0';
                setTimeout(function () {
                    if (msg.parentNode) msg.parentNode.removeChild(msg);
                }, 300);
            }
        });
    });

    console.log('[FoodExpress] Scripts loaded.');
});
