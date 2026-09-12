(() => {
  "use strict";

  const SEARCH_URL = "/api/countries/search/";

  let root = null;
  let api = null;
  let els = {};
  let endsAt = null;
  let finished = false;
  let ticker = null;
  let syncSent = false;
  let results = [];
  let activeIndex = -1;
  let guessedCodes = new Set();
  let searchTimer = null;
  let searchController = null;

  // Sav tekst iz baze i nicknameovi idu kroz textContent, nikad innerHTML.
  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  // --- Odbrojavanje ---

  function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    return `${minutes}:${String(seconds % 60).padStart(2, "0")}`;
  }

  function tick() {
    if (!endsAt) return;
    const left = Math.max(0, Math.round((endsAt - Date.now()) / 1000));
    els.timer.textContent = formatTime(left);
    els.timer.classList.toggle("is-urgent", left <= 30 && !finished);

    if (left === 0 && !finished && !syncSent) {
      syncSent = true;
      // Mali nasumični razmak da svi klijenti ne pošalju sync istovremeno.
      setTimeout(() => api.sendAction({ type: "sync" }), Math.random() * 400);
    }
  }

  // --- Autocomplete ---

  function renderResults() {
    const items = results.map((country, index) => {
      const li = el("li", "search-item" + (index === activeIndex ? " is-active" : ""));
      li.append(el("span", "search-title", country.name));
      li.addEventListener("mousedown", (event) => event.preventDefault());
      li.addEventListener("click", () => choose(country));
      return li;
    });
    els.results.replaceChildren(...items);
    els.results.hidden = items.length === 0;
  }

  function clearResults() {
    clearTimeout(searchTimer);
    if (searchController) searchController.abort();
    results = [];
    activeIndex = -1;
    renderResults();
  }

  async function search(query) {
    if (searchController) searchController.abort();
    if (query.length < 2) {
      clearResults();
      return;
    }
    searchController = new AbortController();
    try {
      const response = await fetch(`${SEARCH_URL}?q=${encodeURIComponent(query)}`, {
        signal: searchController.signal,
      });
      const data = await response.json();
      results = data.results.filter((country) => !guessedCodes.has(country.code));
      activeIndex = results.length ? 0 : -1;
      renderResults();
    } catch (error) {
      if (error.name !== "AbortError") clearResults();
    }
  }

  function choose(country) {
    api.sendAction({ type: "guess", code: country.code });
    els.input.value = "";
    clearResults();
  }

  function onKeyDown(event) {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      if (!results.length) return;
      event.preventDefault();
      const step = event.key === "ArrowDown" ? 1 : -1;
      activeIndex = (activeIndex + step + results.length) % results.length;
      renderResults();
    } else if (event.key === "Enter") {
      event.preventDefault();
      if (results[activeIndex]) choose(results[activeIndex]);
    } else if (event.key === "Escape") {
      clearResults();
    }
  }

  // --- Tragovi ---

  function clueCard(clue, state) {
    const owned = clue.value !== null;
    const row = el("button", "clue-row" + (owned ? " is-owned" : ""));
    row.type = "button";

    const label = el("span", "clue-name");
    label.append(el("span", "clue-emoji", clue.emoji), el("span", null, clue.label));
    row.append(label);

    if (owned) {
      row.append(el("span", "clue-answer", clue.value));
      row.disabled = true;
      return row;
    }

    row.append(el("span", "clue-tag", `${clue.price}`));
    const cantAfford = state.me.points < clue.price;
    const limitReached = state.me.clues_used >= state.max_clues;
    row.disabled = state.finished || state.me.solved || cantAfford || limitReached;
    row.addEventListener("click", () => api.sendAction({ type: "buy_clue", clue: clue.key }));
    return row;
  }

  function guessRow(guess) {
    const row = el("li", "country-guess" + (guess.correct ? " is-correct" : ""));
    row.append(el("span", "guess-name", guess.name));
    if (guess.correct) {
      row.append(el("span", "guess-meta", "✓ correct"));
    } else {
      row.append(el("span", "guess-meta", `${guess.distance.toLocaleString()} km`));
      row.append(el("span", "guess-arrow", guess.arrow));
    }
    return row;
  }

  // --- Rezultati ---

  function resultsTable(state) {
    const box = el("section", "results");
    box.append(el("p", "muted", "The country was"));
    box.append(el("h3", "answer-title", state.answer));

    const best = Math.max(...state.results.map((row) => row.score), 1);
    const list = el("div", "result-list");
    const medals = ["🥇", "🥈", "🥉"];

    state.results.forEach((row, index) => {
      const item = el("div", "result-row");
      const head = el("div", "result-head");
      head.append(el("span", "result-rank", medals[index] || `${index + 1}.`));
      head.append(el("span", "result-name", row.nickname));
      head.append(el("span", "result-score", row.score));
      item.append(head);

      const bar = el("div", "result-bar");
      const fill = el("div", "result-fill");
      fill.style.width = `${Math.round((row.score / best) * 100)}%`;
      bar.append(fill);
      item.append(bar);

      const detail = row.solved
        ? `✓ solved with ${row.clues.length} clue${row.clues.length === 1 ? "" : "s"}`
        : "✗ did not solve";
      item.append(el("p", "muted", `${detail} · ${row.wrong} wrong guess${row.wrong === 1 ? "" : "es"}`));
      list.append(item);
    });

    box.append(list);
    box.append(clueUsage(state));
    return box;
  }

  function clueUsage(state) {
    // Tek sada se otkriva tko je što kupio.
    const keys = state.clues.map((clue) => clue.key);
    const labels = Object.fromEntries(state.clues.map((clue) => [clue.key, clue.label]));

    const table = el("table", "clue-usage");
    const headRow = el("tr");
    headRow.append(el("th", null, "Clue"));
    for (const row of state.results) headRow.append(el("th", null, row.nickname));
    table.append(el("thead").appendChild(headRow).parentNode);

    const body = el("tbody");
    for (const key of keys) {
      if (!state.results.some((row) => row.clues.includes(key))) continue;
      const tr = el("tr");
      tr.append(el("td", "usage-label", labels[key]));
      for (const row of state.results) {
        tr.append(el("td", "usage-cell", row.clues.includes(key) ? "✓" : ""));
      }
      body.append(tr);
    }
    table.append(body);

    const wrapper = el("div", "usage-wrapper");
    wrapper.append(el("h4", "section-title", "Clue usage"));
    wrapper.append(table);
    return wrapper;
  }

  // --- Registracija ---

  PuzzleGames.register("country", {
    mount(rootElement, gameApi) {
      root = rootElement;
      api = gameApi;
      root.innerHTML = `
        <div class="detective">
          <header class="detective-head">
            <div>
              <p class="muted">Mystery country</p>
              <h2 class="mystery">?????</h2>
            </div>
            <div class="detective-stats">
              <span class="timer" data-timer>--:--</span>
              <span class="points" data-points></span>
            </div>
          </header>

          <div data-live>
            <div class="movie-search">
              <input class="input" data-search placeholder="Guess a country…"
                     autocomplete="off" spellcheck="false">
              <ul class="search-results" data-results hidden></ul>
            </div>

            <div class="detective-body">
              <div class="detective-main">
                <p class="muted" data-limit></p>
                <div class="clue-list" data-clues></div>
                <hr class="divider">
                <ul class="guess-log" data-guesses></ul>
              </div>
              <aside class="detective-side">
                <h4 class="section-title">Other detectives</h4>
                <ul class="player-progress" data-progress></ul>
              </aside>
            </div>
          </div>

          <div data-results-view hidden></div>
        </div>`;

      els = {
        timer: root.querySelector("[data-timer]"),
        points: root.querySelector("[data-points]"),
        live: root.querySelector("[data-live]"),
        input: root.querySelector("[data-search]"),
        results: root.querySelector("[data-results]"),
        limit: root.querySelector("[data-limit]"),
        clues: root.querySelector("[data-clues]"),
        guesses: root.querySelector("[data-guesses]"),
        progress: root.querySelector("[data-progress]"),
        resultsView: root.querySelector("[data-results-view]"),
      };

      els.input.addEventListener("input", () => {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(() => search(els.input.value.trim()), 250);
      });
      els.input.addEventListener("keydown", onKeyDown);
      els.input.addEventListener("blur", clearResults);

      ticker = setInterval(tick, 1000);
    },

    update(state) {
      endsAt = new Date(state.ends_at).getTime();
      if (!state.finished) syncSent = false;
      finished = state.finished;
      guessedCodes = new Set(state.me.guesses.map((guess) => guess.code));
      tick();

      els.points.textContent = `${state.me.points} pts`;

      if (state.finished) {
        clearResults();
        els.live.hidden = true;
        els.resultsView.replaceChildren(resultsTable(state));
        els.resultsView.hidden = false;
        return;
      }

      els.resultsView.hidden = true;
      els.live.hidden = false;

      const locked = state.me.solved;
      els.input.disabled = locked;
      els.input.placeholder = locked ? "You solved it! Waiting for the others…" : "Guess a country…";
      els.limit.textContent = `Clues: ${state.me.clues_used} / ${state.max_clues}`;

      els.clues.replaceChildren(...state.clues.map((clue) => clueCard(clue, state)));
      els.guesses.replaceChildren(...[...state.me.guesses].reverse().map(guessRow));

      els.progress.replaceChildren(
        ...state.players.map((player) => {
          const li = el("li", "progress-row");
          li.append(el("span", "progress-name", player.nickname));
          const status = player.solved
            ? "✓ solved"
            : `${player.clues_used} clues · ${player.guesses} guesses`;
          li.append(el("span", "muted", status));
          return li;
        })
      );
    },

    unmount() {
      clearInterval(ticker);
      clearResults();
      root.innerHTML = "";
      els = {};
      endsAt = null;
      finished = false;
    },
  });
})();