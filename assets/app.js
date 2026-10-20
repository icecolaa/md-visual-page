(function () {
  'use strict';

  var docEl = document.documentElement;
  var sidebar = document.getElementById('sidebar');
  var overlay = document.getElementById('overlay');
  var menuBtn = document.getElementById('menuBtn');
  var searchTrigger = document.getElementById('searchTrigger');
  var searchInput = document.getElementById('navSearch');
  var navEmpty = document.getElementById('navEmpty');
  var progressBar = document.getElementById('progressBar');
  var backTop = document.getElementById('backTop');
  var topbar = document.getElementById('topbar');

  function each(list, fn) {
    Array.prototype.forEach.call(list, fn);
  }

  function hasClass(el, className) {
    if (!el || !el.className) {
      return false;
    }
    return (' ' + el.className + ' ').indexOf(' ' + className + ' ') !== -1;
  }

  function addClass(el, className) {
    if (el && !hasClass(el, className)) {
      el.className = el.className ? el.className + ' ' + className : className;
    }
  }

  function removeClass(el, className) {
    if (!el || !el.className) {
      return;
    }
    el.className = (' ' + el.className + ' ')
      .replace(' ' + className + ' ', ' ')
      .replace(/^\s+|\s+$/g, '')
      .replace(/\s+/g, ' ');
  }

  function closestByClass(el, className) {
    var node = el;
    while (node && node.nodeType === 1) {
      if (hasClass(node, className)) {
        return node;
      }
      node = node.parentNode;
    }
    return null;
  }

  function setExpanded(item, open) {
    if (!item) {
      return;
    }
    var btn = item.querySelector('.nav-expand');
    var subs = item.querySelector('.nav-subs');
    if (btn) {
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    }
    if (subs) {
      if (open) {
        subs.removeAttribute('hidden');
      } else {
        subs.setAttribute('hidden', 'hidden');
      }
    }
  }

  function openNav() {
    if (!sidebar || !overlay || !menuBtn) {
      return;
    }
    addClass(sidebar, 'is-open');
    overlay.removeAttribute('hidden');
    menuBtn.setAttribute('aria-expanded', 'true');
    menuBtn.setAttribute('aria-label', '关闭目录');
  }

  function closeNav() {
    if (!sidebar || !overlay || !menuBtn) {
      return;
    }
    removeClass(sidebar, 'is-open');
    overlay.setAttribute('hidden', 'hidden');
    menuBtn.setAttribute('aria-expanded', 'false');
    menuBtn.setAttribute('aria-label', '打开目录');
  }

  if (menuBtn) {
    menuBtn.addEventListener('click', function () {
      if (hasClass(sidebar, 'is-open')) {
        closeNav();
      } else {
        openNav();
      }
    });
  }

  if (overlay) {
    overlay.addEventListener('click', closeNav);
  }

  if (searchTrigger) {
    searchTrigger.addEventListener('click', function () {
      if (window.innerWidth <= 1100) {
        openNav();
      }
      if (searchInput) {
        window.setTimeout(function () {
          searchInput.focus();
        }, 60);
      }
    });
  }

  each(document.querySelectorAll('.nav-expand'), function (btn) {
    btn.addEventListener('click', function () {
      var item = closestByClass(btn, 'nav-item');
      var expanded = btn.getAttribute('aria-expanded') === 'true';
      setExpanded(item, !expanded);
    });
  });

  each(document.querySelectorAll('.toc a'), function (link) {
    link.addEventListener('click', function () {
      if (window.innerWidth <= 1100) {
        closeNav();
      }
    });
  });

  each(document.querySelectorAll('.nav-link, .nav-sub, .nav-overview'), function (link) {
    link.addEventListener('click', function () {
      if (window.innerWidth <= 1100) {
        closeNav();
      }
    });
  });

  function filterNav(query) {
    var q = (query || '').replace(/^\s+|\s+$/g, '').toLowerCase();
    var items = document.querySelectorAll('.nav-item');
    var groups = document.querySelectorAll('.nav-group');
    var visible = 0;

    each(items, function (item) {
      var hay = item.getAttribute('data-search') || '';
      var match = !q || hay.toLowerCase().indexOf(q) !== -1;
      if (match) {
        item.removeAttribute('hidden');
        visible += 1;
        if (q) {
          setExpanded(item, true);
        }
      } else {
        item.setAttribute('hidden', 'hidden');
      }
    });

    each(groups, function (group) {
      var hasVisible = group.querySelectorAll('.nav-item:not([hidden])').length > 0;
      if (hasVisible) {
        group.removeAttribute('hidden');
      } else {
        group.setAttribute('hidden', 'hidden');
      }
    });

    if (navEmpty) {
      if (visible === 0) {
        navEmpty.removeAttribute('hidden');
      } else {
        navEmpty.setAttribute('hidden', 'hidden');
      }
    }

    if (!q) {
      each(items, function (item) {
        var link = item.querySelector('.nav-link');
        if (!link || link.className.indexOf('is-active') === -1) {
          setExpanded(item, false);
        }
      });
    }
  }

  if (searchInput) {
    searchInput.addEventListener('input', function () {
      filterNav(searchInput.value);
    });
  }

  function focusSearch() {
    if (!searchInput) {
      return;
    }
    if (window.innerWidth <= 1100) {
      openNav();
    }
    window.setTimeout(function () {
      searchInput.focus();
      searchInput.select();
    }, 60);
  }

  document.addEventListener('keydown', function (event) {
    var key = event.key || '';
    var target = event.target || {};
    var tag = (target.tagName || '').toLowerCase();
    var typing = tag === 'input' || tag === 'textarea' || tag === 'select' || target.isContentEditable;

    if ((event.metaKey || event.ctrlKey) && key.toLowerCase() === 'k') {
      event.preventDefault();
      focusSearch();
      return;
    }

    if (key === '/' && !typing) {
      event.preventDefault();
      focusSearch();
      return;
    }

    if (key === 'Escape') {
      if (searchInput && target === searchInput && searchInput.value) {
        searchInput.value = '';
        filterNav('');
      } else if (sidebar && hasClass(sidebar, 'is-open')) {
        closeNav();
      }
      return;
    }

    if (!typing && key === 'Home' && event.altKey) {
      event.preventDefault();
      window.scrollTo(0, 0);
    }
  });

  var docLinks = {};
  var topicLinks = {};
  each(document.querySelectorAll('.nav-link'), function (link) {
    var href = link.getAttribute('href') || '';
    if (href.charAt(0) === '#') {
      docLinks[href.slice(1)] = link;
    }
  });
  each(document.querySelectorAll('.nav-sub'), function (link) {
    var href = link.getAttribute('href') || '';
    if (href.charAt(0) === '#') {
      topicLinks[href.slice(1)] = link;
    }
  });

  var targets = document.querySelectorAll('article.doc[id], .paper > .topic > h3[id]');
  var currentDocId = '';
  var currentTopicId = '';

  function clearActive() {
    each(document.querySelectorAll('.nav-link.is-active'), function (el) {
      removeClass(el, 'is-active');
    });
    each(document.querySelectorAll('.nav-sub.is-active'), function (el) {
      removeClass(el, 'is-active');
    });
  }

  function updateScrollState() {
    var scrollTop = window.pageYOffset || docEl.scrollTop || 0;
    var barHeight = topbar ? topbar.offsetHeight : 68;
    var threshold = scrollTop + barHeight + 32;
    var docId = '';
    var topicId = '';
    var i;

    for (i = 0; i < targets.length; i += 1) {
      var el = targets[i];
      var top = el.getBoundingClientRect().top + scrollTop;
      if (top <= threshold) {
        if (el.tagName.toLowerCase() === 'article') {
          docId = el.id;
          topicId = '';
        } else {
          topicId = el.id;
        }
      }
    }

    if (docId && docId !== currentDocId) {
      currentDocId = docId;
      if (docLinks[docId]) {
        setExpanded(closestByClass(docLinks[docId], 'nav-item'), true);
      }
    }

    if (topicId !== currentTopicId) {
      currentTopicId = topicId;
    }

    clearActive();

    if (docLinks[docId]) {
      addClass(docLinks[docId], 'is-active');
    }
    if (topicLinks[topicId]) {
      addClass(topicLinks[topicId], 'is-active');
    }

    var maxScroll = docEl.scrollHeight - window.innerHeight;
    var progress = maxScroll > 0 ? (scrollTop / maxScroll) * 100 : 0;
    if (progress < 0) {
      progress = 0;
    }
    if (progress > 100) {
      progress = 100;
    }
    if (progressBar) {
      progressBar.style.width = progress.toFixed(2) + '%';
    }

    if (backTop) {
      if (scrollTop > 600) {
        addClass(backTop, 'is-visible');
      } else {
        removeClass(backTop, 'is-visible');
      }
    }
  }

  var ticking = false;
  var raf = window.requestAnimationFrame || function (fn) {
    return window.setTimeout(fn, 16);
  };

  function onScroll() {
    if (ticking) {
      return;
    }
    ticking = true;
    raf(function () {
      updateScrollState();
      ticking = false;
    });
  }

  window.addEventListener('scroll', onScroll, false);
  window.addEventListener('resize', function () {
    if (window.innerWidth > 1100) {
      closeNav();
    }
    onScroll();
  }, false);

  if (backTop) {
    backTop.addEventListener('click', function () {
      window.scrollTo(0, 0);
    });
  }

  each(document.querySelectorAll('pre'), function (pre) {
    if (closestByClass(pre, 'code-block')) {
      return;
    }
    var code = pre.querySelector('code');
    var wrapper = document.createElement('div');
    wrapper.className = 'code-block';
    pre.parentNode.insertBefore(wrapper, pre);
    wrapper.appendChild(pre);

    var tools = document.createElement('div');
    tools.className = 'code-tools';

    var lang = document.createElement('span');
    lang.className = 'code-lang';
    var langClass = code ? code.className : '';
    var match = langClass.match(/language-([a-z0-9_+-]+)/i);
    lang.textContent = match ? match[1] : 'code';

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'copy-btn';
    btn.textContent = '复制';
    btn.setAttribute('aria-label', '复制这段代码');

    function markDone() {
      btn.textContent = '已复制';
      window.setTimeout(function () {
        btn.textContent = '复制';
      }, 1600);
    }

    function fallbackCopy(text) {
      var area = document.createElement('textarea');
      area.value = text;
      area.setAttribute('readonly', 'readonly');
      area.style.position = 'fixed';
      area.style.left = '-9999px';
      document.body.appendChild(area);
      area.select();
      var ok = false;
      try {
        ok = document.execCommand('copy');
      } catch (err) {
        ok = false;
      }
      document.body.removeChild(area);
      if (ok) {
        markDone();
      } else {
        btn.textContent = '复制失败';
        window.setTimeout(function () {
          btn.textContent = '复制';
        }, 1600);
      }
    }

    btn.addEventListener('click', function () {
      var text = code ? code.textContent : pre.textContent;
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(markDone).catch(function () {
          fallbackCopy(text);
        });
      } else {
        fallbackCopy(text);
      }
    });

    tools.appendChild(lang);
    tools.appendChild(btn);
    wrapper.appendChild(tools);
  });

  each(document.querySelectorAll('img'), function (img) {
    img.addEventListener('error', function () {
      img.setAttribute('data-broken', 'true');
      img.style.display = 'none';
      var fig = closestByClass(img, 'figure');
      if (fig) {
        var cap = fig.querySelector('figcaption');
        if (cap) {
          cap.textContent = '插图加载失败 · 原图未能读取';
        }
      }
    });
  });

  var revealEls = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window) {
    var observer = new IntersectionObserver(function (entries) {
      each(entries, function (entry) {
        if (entry.isIntersecting) {
          addClass(entry.target, 'in');
          observer.unobserve(entry.target);
        }
      });
    }, { rootMargin: '0px 0px -32px 0px', threshold: 0.06 });
    each(revealEls, function (el) {
      observer.observe(el);
    });
  } else {
    each(revealEls, function (el) {
      addClass(el, 'in');
    });
  }

  var hash = window.location.hash ? window.location.hash.slice(1) : '';
  if (hash) {
    var navLink = docLinks[hash] || topicLinks[hash];
    if (navLink) {
      setExpanded(closestByClass(navLink, 'nav-item'), true);
    }
  }

  updateScrollState();
}());
