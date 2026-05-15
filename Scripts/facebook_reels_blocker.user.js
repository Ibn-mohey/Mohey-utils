// ==UserScript==
// @name         Facebook Reels Scroll Blocker
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Blocks scrolling between Facebook Reels and disables navigation arrows
// @author       ibn-Mohey
// @match        https://www.facebook.com/reel/*
// @match        https://www.facebook.com/reels/*
// @grant        none
// @license      MIT
// @run-at       document-start
// ==/UserScript==

(function () {
    'use strict';

    // Block scroll/wheel events on reels containers
    function blockScroll(e) {
        e.stopPropagation();
        e.preventDefault();
    }

    // Block keyboard navigation (arrow keys, space, page up/down)
    function blockKeys(e) {
        const blocked = ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Space', 'PageUp', 'PageDown'];
        if (blocked.includes(e.code)) {
            e.stopPropagation();
            e.preventDefault();
        }
    }

    // Block touch swipe navigation
    function blockTouch(e) {
        if (e.touches.length === 1) {
            e.stopPropagation();
            e.preventDefault();
        }
    }

    // Capture phase listeners to intercept before Facebook handles them
    document.addEventListener('wheel', blockScroll, { capture: true, passive: false });
    document.addEventListener('scroll', blockScroll, { capture: true, passive: false });
    document.addEventListener('keydown', blockKeys, { capture: true });
    document.addEventListener('touchmove', blockTouch, { capture: true, passive: false });

    const ARROW_SELECTOR = [
        '[aria-label="Next Card"]', '[aria-label="Previous Card"]',
        '[aria-label="Next card"]', '[aria-label="Previous card"]',
        '[aria-label="Next Reel"]', '[aria-label="Previous Reel"]',
        '[aria-label="Next reel"]', '[aria-label="Previous reel"]',
        '[aria-label="Next"]', '[aria-label="Previous"]',
    ].join(', ');

    // Check if an element is a navigation arrow
    function isNavArrow(target) {
        const el = target.closest('[aria-label]');
        if (!el) return false;
        const label = el.getAttribute('aria-label');
        return /^(Next|Previous)(\s+(Card|Reel))?$/i.test(label);
    }

    // Block clicks on navigation arrows
    document.addEventListener('click', function (e) {
        if (isNavArrow(e.target)) {
            e.stopImmediatePropagation();
            e.stopPropagation();
            e.preventDefault();
        }
    }, { capture: true });

    // Also block mousedown/pointerdown (Facebook may use these instead of click)
    ['mousedown', 'mouseup', 'pointerdown', 'pointerup'].forEach(evt => {
        document.addEventListener(evt, function (e) {
            if (isNavArrow(e.target)) {
                e.stopImmediatePropagation();
                e.stopPropagation();
                e.preventDefault();
            }
        }, { capture: true });
    });

    // Disable navigation arrows — don't remove them, neutralize them in place
    const style = document.createElement('style');
    style.textContent = `
        /* Neutralize next/prev arrows on reels */
        ${ARROW_SELECTOR} {
            pointer-events: none !important;
            opacity: 0.2 !important;
        }
    `;
    document.head
        ? document.head.appendChild(style)
        : document.addEventListener('DOMContentLoaded', () => document.head.appendChild(style));

    // Continuously neutralize arrow buttons — remove click handlers by replacing with clones
    const neutralized = new WeakSet();
    const observer = new MutationObserver(() => {
        document.querySelectorAll(ARROW_SELECTOR).forEach(el => {
            if (neutralized.has(el)) return;
            neutralized.add(el);
            // Remove all event listeners by cloning
            const clone = el.cloneNode(true);
            clone.style.pointerEvents = 'none';
            clone.removeAttribute('role');
            clone.removeAttribute('tabindex');
            clone.onclick = (e) => { e.stopImmediatePropagation(); e.preventDefault(); return false; };
            el.parentNode.replaceChild(clone, el);
            neutralized.add(clone);

            // Also disable the immediate parent wrapper of the arrow only
            const wrapper = clone.parentElement;
            if (wrapper) {
                wrapper.style.pointerEvents = 'none';
            }
        });
    });

    const startObserver = () => observer.observe(document.body, { childList: true, subtree: true });

    if (document.body) startObserver();
    else document.addEventListener('DOMContentLoaded', startObserver);

    console.log('[Reels Blocker] Active – scrolling and arrows disabled.');
})();
