(() => {
  const rail = document.getElementById("rail");
  const railToggle = document.getElementById("rail-toggle");
  const menu = document.getElementById("menu");
  const main = document.getElementById("main");
  const search = document.getElementById("search");
  const searchResults = document.getElementById("search-results");
  const contextTitle = document.getElementById("context-title");
  const sectionOutline = document.getElementById("section-outline");
  const contextProgress = document.getElementById("context-progress");
  const links = [
    ...document.querySelectorAll("[data-view], .step-map a[href^='#view-']"),
  ];
  const views = [...document.querySelectorAll(".view")];
  const topic = document.querySelector("[data-od-id='topic-title']").textContent.trim();
  const runId = document.body.dataset.runId.trim();
  const storageKey = "learn-loop:v2:" + runId;
  const legacyStorageKey = "learn-loop:" + document.title;
  const desktopQuery = window.matchMedia("(min-width: 901px)");
  const reducedMotionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");

  function blankState() {
    return {
      cards: {},
      read: {},
      lastView: "",
      railCollapsed: false,
    };
  }

  function normalizeState(parsed) {
    const next = parsed && typeof parsed === "object" ? parsed : blankState();
    if (!next.cards || typeof next.cards !== "object") {
      next.cards = {};
    }
    if (!next.read || typeof next.read !== "object") {
      next.read = {};
    }
    if (typeof next.lastView !== "string") {
      next.lastView = "";
    }
    if (typeof next.railCollapsed !== "boolean") {
      next.railCollapsed = false;
    }
    return next;
  }

  function readStoredState(key) {
    try {
      const saved = localStorage.getItem(key);
      return saved ? normalizeState(JSON.parse(saved)) : null;
    } catch (error) {
      return null;
    }
  }

  function loadState() {
    const current = readStoredState(storageKey);
    if (current) {
      return current;
    }
    const legacy = readStoredState(legacyStorageKey);
    return legacy || blankState();
  }

  const state = loadState();

  function saveState() {
    try {
      localStorage.setItem(storageKey, JSON.stringify(state));
    } catch (error) {
      // 状态在当前页面会话内仍然可用。
    }
  }

  function viewIdForLink(link) {
    if (link.dataset.view) {
      return link.dataset.view;
    }
    return link.getAttribute("href").slice(1);
  }

  function titleForView(view) {
    const heading = view.querySelector("h1, h2");
    return heading ? heading.textContent.trim() : view.id;
  }

  function closeMenu() {
    rail.classList.remove("open");
    menu.setAttribute("aria-expanded", "false");
    menu.setAttribute("aria-label", "打开目录");
  }

  function setRailCollapsed(collapsed, persist) {
    const applied = desktopQuery.matches && collapsed;
    rail.classList.toggle("collapsed", applied);
    main.classList.toggle("rail-collapsed", applied);
    railToggle.textContent = applied ? "▶" : "◀";
    railToggle.setAttribute("aria-expanded", String(!applied));
    railToggle.setAttribute("aria-label", applied ? "展开目录" : "收起目录");
    if (persist) {
      state.railCollapsed = collapsed;
      saveState();
    }
  }

  function updateContextProgress(view) {
    const isRead = Boolean(state.read["read:" + view.id]);
    const deck = view.querySelector(".deck");
    const parts = [isRead ? "阅读状态：已读" : "阅读状态：未标记"];
    if (deck) {
      const cards = [...deck.children].filter((child) => child.matches(".flash"));
      const known = cards.filter((card) => card.dataset.self === "known").length;
      const shaky = cards.filter((card) => card.dataset.self === "shaky").length;
      const unknown = cards.filter((card) => card.dataset.self === "unknown").length;
      parts.push("本机练习：掌握 " + known + " · 模糊 " + shaky + " · 未掌握 " + unknown);
    }
    contextProgress.textContent = parts.join("\n");
  }

  function focusHeading(heading) {
    heading.tabIndex = -1;
    const top = heading.getBoundingClientRect().top + window.scrollY - 30;
    window.scrollTo({
      top,
      behavior: reducedMotionQuery.matches ? "auto" : "smooth",
    });
    try {
      heading.focus({ preventScroll: true });
    } catch (error) {
      heading.focus();
    }
  }

  function outlineHeadingsFor(view) {
    if (view.dataset.module === "perspectives") {
      return [...view.querySelectorAll(".prose > h4[id^='persona-']")];
    }
    return [...view.querySelectorAll(".prose > h3")];
  }

  function updateContext(view) {
    contextTitle.textContent = view.id === "view-intro" ? "学习地图" : titleForView(view);
    sectionOutline.replaceChildren();
    const headings = outlineHeadingsFor(view);
    if (!headings.length) {
      const empty = document.createElement("span");
      empty.textContent = "本章内容较短，无需章内导航。";
      sectionOutline.append(empty);
    } else {
      headings.forEach((heading, index) => {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = heading.textContent.trim();
        button.dataset.odId = view.id + "-outline-" + String(index + 1);
        button.addEventListener("click", () => focusHeading(heading));
        sectionOutline.append(button);
      });
    }
    updateContextProgress(view);
  }

  function show(id) {
    const target = views.find((view) => view.id === id);
    if (!target) {
      return;
    }
    views.forEach((view) => {
      view.classList.toggle("active", view === target);
    });
    links.forEach((link) => {
      const active = viewIdForLink(link) === id;
      link.classList.toggle("active", active);
      if (active) {
        link.setAttribute("aria-current", "page");
      } else {
        link.removeAttribute("aria-current");
      }
    });
    if (id !== "view-intro") {
      state.lastView = id;
      saveState();
    }
    try {
      if (history.replaceState) {
        history.replaceState(null, "", "#" + id);
      }
    } catch (error) {
      location.hash = id;
    }
    closeMenu();
    window.scrollTo(0, 0);
    updateContext(target);
    const heading = target.querySelector("h1, h2");
    if (heading) {
      heading.tabIndex = -1;
      try {
        heading.focus({ preventScroll: true });
      } catch (error) {
        heading.focus();
      }
    }
  }

  links.forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      show(viewIdForLink(link));
    });
  });

  menu.addEventListener("click", () => {
    const open = !rail.classList.contains("open");
    rail.classList.toggle("open", open);
    menu.setAttribute("aria-expanded", String(open));
    menu.setAttribute("aria-label", open ? "关闭目录" : "打开目录");
  });

  railToggle.addEventListener("click", () => {
    setRailCollapsed(!rail.classList.contains("collapsed"), true);
  });

  desktopQuery.addEventListener("change", () => {
    closeMenu();
    setRailCollapsed(state.railCollapsed, false);
  });

  main.addEventListener("click", () => {
    if (!desktopQuery.matches) {
      closeMenu();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeMenu();
    }
  });

  function hashText(text) {
    let hash = 5381;
    for (let index = 0; index < text.length; index += 1) {
      hash = (hash * 33) ^ text.charCodeAt(index);
    }
    return (hash >>> 0).toString(36);
  }

  function assignInspectableIds() {
    views.forEach((view) => {
      const prefix = view.id.replace(/^view-/, "");
      [
        [".card", "card"],
        [".persona", "persona"],
        [".rung", "rung"],
        [".flash", "flash"],
      ].forEach(([selector, label]) => {
        view.querySelectorAll(selector).forEach((element, index) => {
          if (!element.dataset.odId) {
            element.dataset.odId = prefix + "-" + label + "-" + String(index + 1);
          }
        });
      });
      view.querySelectorAll(".step-map a").forEach((element, index) => {
        if (!element.dataset.odId) {
          element.dataset.odId = "learning-map-step-" + String(index + 1);
        }
      });
    });
  }

  assignInspectableIds();

  function setupDeck(deck) {
    const cards = [...deck.children].filter((child) => child.matches(".flash"));
    if (!cards.length) {
      return;
    }

    const toolbar = document.createElement("div");
    toolbar.className = "deck-tools";
    toolbar.dataset.odId = deck.id + "-tools";
    const shuffleButton = document.createElement("button");
    shuffleButton.type = "button";
    shuffleButton.textContent = "洗牌重练";
    const weakButton = document.createElement("button");
    weakButton.type = "button";
    weakButton.textContent = "只看薄弱项";
    weakButton.setAttribute("aria-pressed", "false");
    const collapseButton = document.createElement("button");
    collapseButton.type = "button";
    collapseButton.textContent = "全部收起";
    const resetButton = document.createElement("button");
    resetButton.type = "button";
    resetButton.textContent = "重置本机自评";
    const progress = document.createElement("span");
    progress.className = "deck-progress";
    progress.setAttribute("aria-live", "polite");
    toolbar.append(shuffleButton, weakButton, collapseButton, resetButton, progress);
    deck.before(toolbar);

    const empty = document.createElement("div");
    empty.className = "deck-empty";
    empty.textContent = "当前没有薄弱项。可查看全部题目或重置本机自评。";
    deck.append(empty);

    const entries = [];
    cards.forEach((card) => {
      const summary = card.querySelector("summary");
      const answer = card.querySelector(".flash-answer");
      if (!summary || !answer) {
        return;
      }
      const cardKey = deck.id + ":" + hashText(summary.textContent.trim());
      const assessment = document.createElement("div");
      assessment.className = "self-assessment";
      const note = document.createElement("span");
      note.textContent = "本机练习，不计入真实施考记录。";
      assessment.append(note);
      const buttons = {};
      [
        ["known", "掌握"],
        ["shaky", "模糊"],
        ["unknown", "未掌握"],
      ].forEach(([value, label]) => {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = label;
        button.addEventListener("click", () => {
          state.cards[cardKey] = state.cards[cardKey] === value ? undefined : value;
          if (state.cards[cardKey] === undefined) {
            delete state.cards[cardKey];
          }
          saveState();
          render();
        });
        buttons[value] = button;
        assessment.append(button);
      });
      answer.append(assessment);
      entries.push({
        card,
        cardKey,
        buttons,
      });
    });

    function render() {
      const counts = {
        known: 0,
        shaky: 0,
        unknown: 0,
      };
      entries.forEach((entry) => {
        const value = state.cards[entry.cardKey];
        if (value === "known" || value === "shaky" || value === "unknown") {
          entry.card.dataset.self = value;
          counts[value] += 1;
        } else {
          delete entry.card.dataset.self;
        }
        Object.entries(entry.buttons).forEach(([buttonValue, button]) => {
          button.setAttribute("aria-pressed", String(value === buttonValue));
        });
      });
      const untouched = entries.length - counts.known - counts.shaky - counts.unknown;
      progress.textContent =
        "掌握 " + counts.known + " · 模糊 " + counts.shaky + " · 未掌握 " + counts.unknown + " · 未练 " + untouched;
      const weakCount = counts.shaky + counts.unknown + untouched;
      deck.classList.toggle("is-empty", deck.classList.contains("only-weak") && weakCount === 0);
      const activeView = deck.closest(".view");
      if (activeView && activeView.classList.contains("active")) {
        updateContextProgress(activeView);
      }
    }

    shuffleButton.addEventListener("click", () => {
      const shuffled = [...cards];
      for (let index = shuffled.length - 1; index > 0; index -= 1) {
        const other = Math.floor(Math.random() * (index + 1));
        const current = shuffled[index];
        shuffled[index] = shuffled[other];
        shuffled[other] = current;
      }
      shuffled.forEach((card, index) => {
        card.style.order = String(index);
        card.open = false;
      });
    });

    weakButton.addEventListener("click", () => {
      const onlyWeak = deck.classList.toggle("only-weak");
      weakButton.setAttribute("aria-pressed", String(onlyWeak));
      weakButton.textContent = onlyWeak ? "查看全部题目" : "只看薄弱项";
      render();
    });

    collapseButton.addEventListener("click", () => {
      cards.forEach((card) => {
        card.open = false;
      });
    });

    resetButton.addEventListener("click", () => {
      if (!window.confirm("清空这组题目的本机自评？真实施考记录不会受到影响。")) {
        return;
      }
      entries.forEach((entry) => {
        delete state.cards[entry.cardKey];
      });
      saveState();
      render();
    });

    render();
  }

  document.querySelectorAll(".deck").forEach(setupDeck);

  function syncReadState(view, button) {
    const value = Boolean(state.read["read:" + view.id]);
    button.textContent = value ? "✓ 本章已读" : "标记本章已读";
    button.setAttribute("aria-pressed", String(value));
    links.forEach((link) => {
      if (viewIdForLink(link) === view.id) {
        link.classList.toggle("read", value);
      }
    });
    if (view.classList.contains("active")) {
      updateContextProgress(view);
    }
  }

  views.forEach((view) => {
    const head = view.querySelector(".step-head");
    if (!head) {
      return;
    }
    const button = document.createElement("button");
    button.type = "button";
    button.className = "read-toggle";
    button.dataset.odId = view.id + "-read-toggle";
    head.append(button);
    button.addEventListener("click", () => {
      const key = "read:" + view.id;
      state.read[key] = !state.read[key];
      saveState();
      syncReadState(view, button);
    });
    syncReadState(view, button);
  });

  function countMatches(text, query) {
    let count = 0;
    let position = 0;
    while (position < text.length) {
      const matchAt = text.indexOf(query, position);
      if (matchAt < 0) {
        break;
      }
      count += 1;
      position = matchAt + Math.max(1, query.length);
    }
    return count;
  }

  const searchIndex = [];
  views.forEach((view) => {
    const title = titleForView(view);
    const evidence = view.querySelector(".evidence");
    const bodyClone = view.cloneNode(true);
    bodyClone.querySelectorAll(".evidence, .flash-answer").forEach((node) => node.remove());
    [
      ["标题", title],
      ["正文", bodyClone.textContent],
      ["取证", evidence ? evidence.textContent : ""],
    ].forEach(([category, value]) => {
      const text = value.replace(/\s+/g, " ").trim();
      if (text) {
        searchIndex.push({
          view,
          title,
          category,
          text,
        });
      }
    });
  });

  function showSearchResults(query) {
    searchResults.replaceChildren();
    const normalized = query.trim().toLocaleLowerCase();
    if (normalized.length < 2) {
      return;
    }
    const matches = searchIndex
      .map((entry) => {
        const haystack = entry.text.toLocaleLowerCase();
        return {
          entry,
          matchAt: haystack.indexOf(normalized),
          count: countMatches(haystack, normalized),
        };
      })
      .filter((match) => match.matchAt >= 0)
      .sort((left, right) => {
        const leftPriority = left.entry.category === "标题" ? 0 : 1;
        const rightPriority = right.entry.category === "标题" ? 0 : 1;
        return leftPriority - rightPriority || right.count - left.count;
      });

    matches.slice(0, 8).forEach((match) => {
      const start = Math.max(0, match.matchAt - 28);
      const end = Math.min(match.entry.text.length, match.matchAt + normalized.length + 40);
      const snippet =
        (start > 0 ? "…" : "") +
        match.entry.text.slice(start, end) +
        (end < match.entry.text.length ? "…" : "");
      const result = document.createElement("button");
      result.type = "button";
      result.className = "search-result";
      const title = document.createElement("strong");
      title.textContent = match.entry.title;
      const preview = document.createElement("span");
      preview.textContent = snippet;
      const meta = document.createElement("small");
      meta.textContent = match.entry.category + " · " + match.count + " 处命中";
      result.append(title, preview, meta);
      result.addEventListener("click", () => {
        show(match.entry.view.id);
        match.entry.view.classList.remove("hit-flash");
        void match.entry.view.offsetWidth;
        match.entry.view.classList.add("hit-flash");
        window.setTimeout(() => {
          match.entry.view.classList.remove("hit-flash");
        }, 1200);
      });
      searchResults.append(result);
    });

    if (!matches.length) {
      const empty = document.createElement("div");
      empty.className = "search-result";
      empty.textContent = "未找到匹配内容";
      searchResults.append(empty);
    }
  }

  search.addEventListener("input", () => {
    showSearchResults(search.value);
  });

  views.forEach((view, index) => {
    const navigation = document.createElement("nav");
    navigation.className = "lesson-nav";
    navigation.dataset.odId = view.id + "-lesson-nav";
    navigation.setAttribute("aria-label", "连续学习导航");
    const previous = index > 0 ? views[index - 1] : null;
    const next = index < views.length - 1 ? views[index + 1] : views[0];
    [
      [previous, "上一步", "←"],
      [next, next === views[0] ? "回到地图" : "推荐下一步", "→"],
    ].forEach(([target, label, arrow]) => {
      if (!target) {
        const spacer = document.createElement("span");
        navigation.append(spacer);
        return;
      }
      const button = document.createElement("button");
      button.type = "button";
      const meta = document.createElement("small");
      meta.textContent = label;
      const text = document.createElement("span");
      text.textContent = label === "上一步" ? arrow + " " + titleForView(target) : titleForView(target) + " " + arrow;
      button.append(meta, text);
      button.addEventListener("click", () => show(target.id));
      navigation.append(button);
    });
    view.append(navigation);
  });

  const intro = document.getElementById("view-intro");
  const introLead = intro.querySelector(".lead");
  const resumeCard = document.createElement("div");
  resumeCard.className = "resume-card";
  resumeCard.dataset.odId = "resume-learning";
  const resumeCopy = document.createElement("div");
  const resumeTitle = document.createElement("strong");
  const resumeNote = document.createElement("span");
  const resumeButton = document.createElement("button");
  resumeButton.type = "button";
  resumeButton.className = "resume-button";
  resumeCopy.append(resumeTitle, resumeNote);
  resumeCard.append(resumeCopy, resumeButton);
  introLead.after(resumeCard);

  function renderResumeCard() {
    const lastView = views.find((view) => view.id === state.lastView);
    const readCount = views.filter((view) => state.read["read:" + view.id]).length;
    resumeTitle.textContent = lastView ? "继续上次学习" : "从推荐路径开始";
    resumeNote.textContent = "阅读进度 " + readCount + "/" + (views.length - 1) + " 章";
    resumeButton.textContent = lastView ? "继续：" + titleForView(lastView) : "开始学习";
    resumeButton.onclick = () => show(lastView ? lastView.id : "view-10");
  }

  renderResumeCard();

  function copyText(value, button) {
    const done = () => {
      const original = button.textContent;
      button.textContent = "已复制";
      window.setTimeout(() => {
        button.textContent = original;
      }, 1200);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(value).then(done).catch(() => {
        window.prompt("复制以下内容后回到对话中发送：", value);
      });
    } else {
      window.prompt("复制以下内容后回到对话中发送：", value);
    }
  }

  document.querySelectorAll(".status[data-workflow-command]").forEach((status) => {
    const command = status.dataset.workflowCommand;
    const original = status.textContent.trim();
    const copy = document.createElement("div");
    copy.textContent = original;
    const boundary = document.createElement("span");
    boundary.className = "status-copy";
    boundary.textContent = "真实练习将在对话中进行；本页不会代答或写入会话记录。";
    copy.append(boundary);
    const button = document.createElement("button");
    button.type = "button";
    button.className = "workflow-copy";
    button.textContent = "复制“" + command + "”提示词";
    button.dataset.odId = status.closest(".view").id + "-workflow-copy";
    button.addEventListener("click", () => copyText(command + " " + topic, button));
    status.replaceChildren(copy, button);
  });

  let printState = null;
  window.addEventListener("beforeprint", () => {
    const active = views.find((view) => view.classList.contains("active"));
    printState = active ? active.id : "view-intro";
    views.forEach((view) => view.classList.add("active"));
    document.querySelectorAll("details:not([open])").forEach((details) => {
      details.dataset.printOpen = "true";
      details.open = true;
    });
  });

  window.addEventListener("afterprint", () => {
    document.querySelectorAll("details[data-print-open]").forEach((details) => {
      details.open = false;
      delete details.dataset.printOpen;
    });
    views.forEach((view) => {
      view.classList.toggle("active", view.id === printState);
    });
    printState = null;
  });

  setRailCollapsed(state.railCollapsed, false);
  const initial = location.hash.slice(1);
  show(views.some((view) => view.id === initial) ? initial : "view-intro");
})();
