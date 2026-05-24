// ==UserScript==
// @name         Facebook Reels Scroll Blocker
// @namespace    http://tampermonkey.net/
// @version      1.2
// @description  Blocks scrolling between Facebook Reels, disables navigation arrows, stops auto-loop, and limits reel preloading
// @author       ibn-Mohey
// @match        https://www.facebook.com/*
// @grant        none
// @license      MIT
// @run-at       document-start
// ==/UserScript==

(function () {
    'use strict';

    // ── Hook into SPA navigation ──
    // Facebook uses history.pushState/replaceState for navigation — we intercept them
    const _pushState = history.pushState;
    const _replaceState = history.replaceState;
    history.pushState = function () {
        _pushState.apply(this, arguments);
        onNavigation();
    };
    history.replaceState = function () {
        _replaceState.apply(this, arguments);
        onNavigation();
    };
    window.addEventListener('popstate', onNavigation);

    function onNavigation() {
        console.log('[Reels Blocker] Navigation detected:', window.location.pathname);
        // Re-attach observers after a short delay (DOM needs to update)
        setTimeout(reAttach, 300);
        setTimeout(reAttach, 1000);
        setTimeout(reAttach, 2500);
    }

    function reAttach() {
        if (!isReelsPage()) return;
        console.log('[Reels Blocker] Reels page detected, re-attaching...');
        attachObservers();
        disableAutoLoop();
        limitReelsChildren();
    }

    // Block keyboard navigation (arrow keys, space, page up/down)
    function blockKeys(e) {
        if (!isReelsPage()) return;
        const blocked = ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'PageUp', 'PageDown'];
        if (blocked.includes(e.code)) {
            e.stopPropagation();
            e.preventDefault();
        }
    }

    // Block touch swipe navigation
    function blockTouch(e) {
        if (!isReelsPage()) return;
        if (e.touches.length === 1) {
            e.stopPropagation();
            e.preventDefault();
        }
    }

    // Capture phase listeners to intercept before Facebook handles them
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

    // Check if we're viewing a reel
    function isReelsPage() {
        if (/\/reel(s)?[\/\?]?/i.test(window.location.pathname)) return true;
        if (document.querySelector(ARROW_SELECTOR)) return true;
        const dialogs = document.querySelectorAll('[role="dialog"]');
        for (const d of dialogs) {
            if (d.querySelector('video')) return true;
        }
        return false;
    }

    // ── Block programmatic scrolling (how Facebook actually navigates reels) ──
    // Facebook scrolls a container to move between reels — intercept scroll methods
    const _origScrollTo = Element.prototype.scrollTo;
    const _origScrollBy = Element.prototype.scrollBy;
    const _origScrollTopSet = Object.getOwnPropertyDescriptor(Element.prototype, 'scrollTop').set;
    const _origScrollTopGet = Object.getOwnPropertyDescriptor(Element.prototype, 'scrollTop').get;

    Element.prototype.scrollTo = function (...args) {
        if (isReelsPage() && this.querySelector && this.querySelector('video')) {
            console.log('[Reels Blocker] Blocked scrollTo on reel container');
            return;
        }
        return _origScrollTo.apply(this, args);
    };

    Element.prototype.scrollBy = function (...args) {
        if (isReelsPage() && this.querySelector && this.querySelector('video')) {
            console.log('[Reels Blocker] Blocked scrollBy on reel container');
            return;
        }
        return _origScrollBy.apply(this, args);
    };

    Object.defineProperty(Element.prototype, 'scrollTop', {
        set(val) {
            if (isReelsPage() && this.querySelector && this.querySelector('video')) {
                console.log('[Reels Blocker] Blocked scrollTop set on reel container');
                return;
            }
            return _origScrollTopSet.call(this, val);
        },
        get() {
            return _origScrollTopGet.call(this);
        },
        configurable: true,
    });

    // Block clicks on navigation arrows
    document.addEventListener('click', function (e) {
        if (!isReelsPage()) return;
        if (isNavArrow(e.target)) {
            e.stopImmediatePropagation();
            e.stopPropagation();
            e.preventDefault();
        }
    }, { capture: true });

    // Also block mousedown/pointerdown (Facebook may use these instead of click)
    ['mousedown', 'mouseup', 'pointerdown', 'pointerup'].forEach(evt => {
        document.addEventListener(evt, function (e) {
            if (!isReelsPage()) return;
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

    // ── Unified function to (re-)attach all observers ──
    function attachObservers() {
        if (!document.body) return;
        // Disconnect first to avoid duplicates
        observer.disconnect();
        videoObserver.disconnect();
        reelsLimiter.disconnect();
        // Re-attach
        observer.observe(document.body, { childList: true, subtree: true });
        videoObserver.observe(document.body, { childList: true, subtree: true });
        reelsLimiter.observe(document.body, { childList: true, subtree: true });
    }

    // ── Stop video auto-loop: pause when it reaches the end ──
    const handledVideos = new WeakSet();

    function disableAutoLoop() {
        document.querySelectorAll('video').forEach(video => {
            if (handledVideos.has(video)) return;
            handledVideos.add(video);

            // Disable the built-in loop attribute
            video.loop = false;

            // Watch for Facebook re-enabling loop
            const loopObserver = new MutationObserver(() => {
                if (video.loop) video.loop = false;
            });
            loopObserver.observe(video, { attributes: true, attributeFilter: ['loop'] });

            // Also override the loop property setter
            try {
                Object.defineProperty(video, 'loop', {
                    get() { return false; },
                    set() { /* block */ },
                    configurable: true,
                });
            } catch (e) { /* ignore if already defined */ }

            // Pause when video ends
            video.addEventListener('ended', () => {
                video.pause();
                // Move to start so clicking/space replays from beginning
                video.currentTime = 0;
            });

            // Fallback: pause if video reaches near the end (some players don't fire 'ended' with loop)
            video.addEventListener('timeupdate', () => {
                if (video.duration && video.currentTime >= video.duration - 0.15) {
                    video.pause();
                    video.currentTime = 0;
                }
            });
        });
    }

    // Run on new video elements added to DOM
    const videoObserver = new MutationObserver(disableAutoLoop);

    // ── Limit reels container: keep only the first reel, remove extras ──
    // The reels container path: div[2]/div[1] holds child divs for each reel
    function limitReelsChildren() {
        // Find containers that hold multiple reel items
        // Target the known structure: a scrollable container with multiple reel children
        document.querySelectorAll('div[style*="translate"]').forEach(container => {
            // Check parent chain matches reels-like structure
            const children = Array.from(container.children).filter(c => c.tagName === 'DIV');
            if (children.length > 1 && children[0].querySelector('video')) {
                // Keep only the first reel child, remove the rest
                children.slice(1).forEach(child => child.remove());
            }
        });

        // Generic approach: find any container with many video-holding siblings
        // and keep only the first
        document.querySelectorAll('video').forEach(video => {
            // Walk up to find the reel item wrapper
            let reelItem = video.closest('div');
            for (let i = 0; i < 5 && reelItem; i++) {
                const parent = reelItem.parentElement;
                if (!parent) break;
                const siblings = Array.from(parent.children).filter(c => c.tagName === 'DIV');
                if (siblings.length > 1 && siblings.indexOf(reelItem) >= 0) {
                    // Check if multiple siblings contain videos (= multiple reels)
                    const videoSiblings = siblings.filter(s => s.querySelector('video'));
                    if (videoSiblings.length > 1) {
                        // Keep only the first one with a video
                        videoSiblings.slice(1).forEach(s => s.remove());
                        console.log(`[Reels Blocker] Removed ${videoSiblings.length - 1} extra reel(s)`);
                        return;
                    }
                }
                reelItem = parent;
            }
        });
    }

    const reelsLimiter = new MutationObserver(() => {
        limitReelsChildren();
    });

    // ── Initial attach ──
    function init() {
        attachObservers();
        disableAutoLoop();
        limitReelsChildren();
        console.log('[Reels Blocker] Active – scrolling, arrows, and auto-loop disabled.');
    }

    if (document.body) init();
    else document.addEventListener('DOMContentLoaded', init);
})();