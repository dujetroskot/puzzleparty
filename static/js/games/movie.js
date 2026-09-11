(() => {
  "use strict";

  const SEARCH_URL = "/api/movies/search/";
  const ARROWS = { up: "↑", down: "↓" };

  let root = null;
  let api = null;
  let els = {};
  let results = [];
  let activeIndex = -1;
  let guessedIds = new Set();
  let searchTimer = null;
  let searchController = null;

  // Sav tekst iz TMDB-a i nickname ide kroz textContent, nikad kroz innerHTML.
  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  function posterNode(url, className) {
    if (!url) return el("div", `${className} poster-empty`, "🎬");
    const img = el("img", className);
    img.src = url;
    img.alt = "";
    img.loading = "lazy";
    return img;
  }

  // --- Autocomplete ---

  function renderResults() {
    const items = results.map((movie, index) => {
      const li = el("li", "search-item" + (index === activeIndex ? " is-active" : ""));
      li.append(posterNode(movie.poster, "search-poster"));
      const text = el("div", "search-text");
      text.append(el("span", "search-title", movie.title), el("span", "muted", movie.year ?? ""));
      li.append(text);
      // preventDefault na mousedown: input ne gubi fokus pa se lista ne zatvori prije klika.
      li.addEventListener("mousedown", (event) => event.preventDefault());
      li.addEventListener("click", () => choose(movie));
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
      results = data.results.filter((movie) => !guessedIds.has(movie.id));
      activeIndex = results.length ? 0 : -1;
      renderResults();
    } catch (error) {
      if (error.name !== "AbortError") clearResults();
    }
  }

  function choose(movie) {
    api.sendAction({ type: "guess", movie_id: movie.id });
    els.input.value = "";
    clearResults();
  }

  function onInput() {
    clearTimeout(searchTimer);
    // Čekamo 250 ms nakon zadnjeg slova, da ne zovemo server za svako slovo.
    searchTimer = setTimeout(() => search(els.input.value.trim()), 250);
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

  // --- Pokušaji ---

  function tile(label, status, wide) {
    const node = el("div", `tile tile-${status}` + (wide ? " tile-wide" : ""));
    node.append(el("span", "tile-label", label));
    return node;
  }

  function numberTile(label, field, unit) {
    const node = tile(label, field.status);
    const value = field.value == null ? "?" : `${field.value}${unit}`;
    const arrow = field.hint ? ` ${ARROWS[field.hint]}` : "";
    node.append(el("span", "tile-value", value + arrow));
    return node;
  }

  function textTile(label, field) {
    const node = tile(label, field.status);
    node.append(el("span", "tile-value", field.value || "?"));
    return node;
  }

  function listTile(label, field, wide = false) {
    const node = tile(label, field.status, wide);
    const chips = el("div", "chips");
    if (!field.items.length) chips.append(el("span", "chip", "—"));
    for (const item of field.items) {
      chips.append(el("span", item.match ? "chip chip-match" : "chip", item.value));
    }
    node.append(chips);
    return node;
  }

  function guessCard(guess) {
    const card = el("article", "movie-guess" + (guess.correct ? " is-correct" : ""));

    const header = el("div", "movie-guess-header");
    const info = el("div");
    info.append(el("h3", "guess-title", guess.movie.title));
    info.append(el("p", "muted", `guessed by ${guess.player}`));
    header.append(posterNode(guess.movie.poster, "guess-poster"), info);

    const tiles = el("div", "tiles");
    tiles.append(
      numberTile("Year", guess.year, ""),
      numberTile("Runtime", guess.runtime, " min"),
      textTile("Language", guess.language),
      listTile("Country", guess.countries),
      listTile("Director", guess.directors),
      listTile("Genres", guess.genres, true),
      listTile("Cast", guess.cast, true)
    );

    card.append(header, tiles);
    return card;
  }

  function renderAnswer(state) {
    if (!state.answer) {
      els.answer.hidden = true;
      els.answer.replaceChildren();
      return;
    }
    const box = el("div", "movie-answer");
    const text = el("div");
    text.append(el("p", "muted", state.solved ? "You got it! The movie was" : "The movie was"));
    text.append(el("h3", "answer-title", `${state.answer.title} (${state.answer.year ?? "?"})`));
    box.append(posterNode(state.answer.poster, "answer-poster"), text);
    els.answer.replaceChildren(box);
    els.answer.hidden = false;
  }

  PuzzleGames.register("movie", {
    mount(rootElement, gameApi) {
      root = rootElement;
      api = gameApi;
      root.innerHTML = `
        <div class="movie-game">
          <div class="movie-search">
            <input class="input" data-search placeholder="Type a movie title…"
                   autocomplete="off" spellcheck="false">
            <ul class="search-results" data-results hidden></ul>
          </div>
          <div data-answer hidden></div>
          <div class="movie-meta">
            <span class="muted" data-count></span>
            <button type="button" class="btn btn-small" data-reveal>Reveal answer</button>
          </div>
          <div class="guess-list" data-guesses></div>
          <p class="attribution">
            Movie data from TMDB. This product uses the TMDB API but is not endorsed or certified by TMDB.
          </p>
        </div>`;
      els = {
        input: root.querySelector("[data-search]"),
        results: root.querySelector("[data-results]"),
        answer: root.querySelector("[data-answer]"),
        count: root.querySelector("[data-count]"),
        reveal: root.querySelector("[data-reveal]"),
        guesses: root.querySelector("[data-guesses]"),
      };
      els.input.addEventListener("input", onInput);
      els.input.addEventListener("keydown", onKeyDown);
      els.input.addEventListener("blur", clearResults);
      els.reveal.addEventListener("click", () => {
        if (confirm("Reveal the answer for everyone?")) api.sendAction({ type: "reveal" });
      });
    },

    update(state) {
      guessedIds = new Set(state.guesses.map((guess) => guess.movie.id));
      const over = state.solved || state.revealed;

      els.input.disabled = over;
      els.reveal.hidden = over;
      if (over) {
        clearResults();
      } else if (results.length) {
        // Netko drugi je možda upravo pogodio film koji je u našoj listi.
        results = results.filter((movie) => !guessedIds.has(movie.id));
        activeIndex = Math.min(activeIndex, results.length - 1);
        renderResults();
      }

      const n = state.guesses.length;
      els.count.textContent = n ? `${n} ${n === 1 ? "guess" : "guesses"}` : "No guesses yet";
      els.guesses.replaceChildren(...[...state.guesses].reverse().map(guessCard));
      renderAnswer(state);
    },

    unmount() {
      clearResults();
      root.innerHTML = "";
      els = {};
    },
  });
})();