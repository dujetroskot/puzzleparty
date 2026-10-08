(() => {
  "use strict";

  const MOVE_INTERVAL = 100; // ms između slanja pozicije serveru
  let announced = false;
  let root = null;
  let api = null;
  let els = {};
  let ticker = null;
  let endsAt = null;
  let syncSent = false;
  let dragging = false;
  let lastSent = 0;
  let moveTimer = null;
  let localValue = 50;

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  function show(name) {
    for (const [key, node] of Object.entries(els.views)) {
      node.hidden = key !== name;
    }
  }

  // --- Timer ---

  function tick() {
    if (!endsAt) {
      els.timer.textContent = "";
      return;
    }
    const left = Math.max(0, Math.round((endsAt - Date.now()) / 1000));
    els.timer.textContent = `${left}s`;
    els.timer.classList.toggle("is-urgent", left <= 10);
    if (left === 0 && !syncSent) {
      syncSent = true;
      setTimeout(() => api.sendAction({ type: "sync" }), Math.random() * 400);
    }
  }

  // --- Klizač ---

  function sendMove(value, lock) {
    if (lock) {
      api.sendAction({ type: "lock", value });
      return;
    }
    // Najviše 10 poruka u sekundi; zadnja se uvijek pošalje.
    clearTimeout(moveTimer);
    const wait = Math.max(0, MOVE_INTERVAL - (Date.now() - lastSent));
    moveTimer = setTimeout(() => {
      lastSent = Date.now();
      api.sendAction({ type: "move", value: localValue });
    }, wait);
  }

  function paintSlider(value) {
    els.slider.value = value;
    els.sliderValue.textContent = value;
  }

  // --- Skala s rezultatima ---

  function resultScale(sub) {
    const scale = el("div", "wave-scale is-reveal");
    scale.append(el("span", "wave-pole", sub.pair[0]));
    const track = el("div", "wave-track");

    const target = el("div", "wave-target");
    target.style.left = `${sub.target}%`;
    track.append(target);

    sub.results
      .filter((row) => !row.is_giver && row.value !== null)
      .forEach((row) => {
        const marker = el("div", "wave-marker");
        marker.style.left = `${row.value}%`;
        marker.append(el("span", "wave-marker-name", row.nickname));
        track.append(marker);
      });

    scale.append(track);
    scale.append(el("span", "wave-pole", sub.pair[1]));
    return scale;
  }

  function resultRows(sub) {
    return sub.results.map((row) => {
      const item = el("li", "wave-result");
      item.append(el("span", "wave-result-name", row.nickname));
      const detail = row.is_giver
        ? "gave the clue"
        : `${row.value} · off by ${Math.abs(row.value - sub.target)}`;
      item.append(el("span", "muted", detail));
      item.append(el("span", "wave-result-points", `+${row.points}`));
      return item;
    });
  }

  // --- Tablica bodova ---

  function scoreboard(rows, big = false) {
    const table = el("table", "scoreboard" + (big ? " is-big" : ""));
    const body = el("tbody");
    const medals = ["🥇", "🥈", "🥉"];
    rows.forEach((row, index) => {
      const tr = el("tr");
      tr.append(el("td", "score-rank", big ? medals[index] || `${index + 1}.` : `${index + 1}.`));
      tr.append(el("td", "score-name", row.nickname));
      tr.append(el("td", "score-total", row.total));
      body.append(tr);
    });
    table.append(body);
    return table;
  }

  // --- Faze ---

  function renderSetup(state) {
    const box = els.views.setup;
    box.replaceChildren();
    box.append(el("h3", "wave-heading", "How many rounds?"));
    box.append(
      el("p", "muted", "One round means everyone gives a clue once.")
    );

    const choices = el("div", "round-choices");
    for (const count of state.round_choices) {
      const button = el("button", "round-choice" + (count === state.rounds ? " is-active" : ""), count);
      button.type = "button";
      button.addEventListener("click", () => api.sendAction({ type: "set_rounds", rounds: count }));
      choices.append(button);
    }
    box.append(choices);

    const players = el("p", "muted", `Players: ${state.players.join(", ")}`);
    box.append(players);

    const start = el("button", "btn btn-primary", "Start game");
    start.type = "button";
    start.disabled = state.players.length < 2;
    start.addEventListener("click", () => api.sendAction({ type: "start" }));
    box.append(start);
    if (state.players.length < 2) {
      box.append(el("p", "muted", "Waiting for at least 2 players…"));
    }
  }

  function renderClue(state) {
    const sub = state.sub;
    const box = els.views.clue;
    box.replaceChildren();

    if (!sub.is_giver) {
      box.append(el("h3", "wave-heading", `${sub.giver} is thinking of a clue…`));
      box.append(el("p", "muted", "The scale stays hidden until the clue arrives."));
      box.append(el("div", "wave-pair", `${sub.pair[0]}  ↔  ${sub.pair[1]}`));
      return;
    }

    box.append(el("h3", "wave-heading", "Your turn to give the clue"));
    const scale = el("div", "wave-scale");
    scale.append(el("span", "wave-pole", sub.pair[0]));
    const track = el("div", "wave-track");
    const target = el("div", "wave-target");
    target.style.left = `${sub.target}%`;
    track.append(target);
    scale.append(track);
    scale.append(el("span", "wave-pole", sub.pair[1]));
    box.append(scale);
    box.append(el("p", "muted", "Give one word or a short phrase that lands on the mark."));

    const row = el("div", "share-row");
    const input = el("input", "input");
    input.placeholder = "Your clue…";
    input.maxLength = 40;
    const submit = el("button", "btn btn-primary", "Send");
    submit.type = "button";
    const send = () => {
      const clue = input.value.trim();
      if (clue) api.sendAction({ type: "submit_clue", clue });
    };
    submit.addEventListener("click", send);
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") send();
    });
    row.append(input, submit);
    box.append(row);
    input.focus();
  }

  function renderGuess(state) {
    const sub = state.sub;
    els.clueText.textContent = sub.clue;
    els.clueGiver.textContent = `from ${sub.giver}`;
    els.poleLeft.textContent = sub.pair[0];
    els.poleRight.textContent = sub.pair[1];
    els.lockCount.textContent = `${sub.locked_count} / ${sub.guesser_count} locked in`;

    const locked = Boolean(sub.my_guess && sub.my_guess.locked);
    els.sliderBox.hidden = sub.is_giver;
    els.giverNote.hidden = !sub.is_giver;

    if (!sub.is_giver) {
      // Ne diramo klizač dok ga korisnik vuče.
      if (!dragging) {
        localValue = sub.my_guess ? sub.my_guess.value : 50;
        paintSlider(localValue);
      }
      els.slider.disabled = locked;
      els.lockButton.disabled = locked;
      els.lockButton.textContent = locked ? "Locked in ✓" : "Lock it in";
    }
  }

  function renderReveal(state) {
    const sub = state.sub;
    const box = els.views.reveal;
    box.replaceChildren();
    box.append(el("h3", "wave-heading", `"${sub.clue}"`));
    box.append(el("p", "muted", `Clue by ${sub.giver} · target was ${sub.target}`));
    box.append(resultScale(sub));

    const list = el("ul", "wave-results");
    list.append(...resultRows(sub));
    box.append(list);

    const next = el("button", "btn btn-primary", "Next round");
    next.type = "button";
    next.addEventListener("click", () => api.sendAction({ type: "next" }));
    box.append(next);
  }

  function renderFinished(state) {
    const box = els.views.finished;
    box.replaceChildren();
    box.append(el("h3", "wave-heading", "Final scores"));
    box.append(scoreboard(state.scoreboard, true));

    const again = el("button", "btn btn-primary", "Play again");
    again.type = "button";
    again.addEventListener("click", () => api.sendAction({ type: "restart" }));
    box.append(again);
  }

  // --- Registracija ---

  PuzzleGames.register("wavelength", {
    mount(rootElement, gameApi) {
      root = rootElement;
      api = gameApi;
      root.innerHTML = `
        <div class="wave">
          <header class="wave-head">
            <span class="muted" data-progress></span>
            <span class="timer" data-timer></span>
          </header>

          <section data-view-setup hidden></section>
          <section data-view-clue hidden></section>

          <section data-view-guess hidden>
            <div class="wave-clue">
              <p class="muted" data-clue-giver></p>
              <h3 class="wave-clue-text" data-clue-text></h3>
            </div>
            <div class="wave-scale">
              <span class="wave-pole" data-pole-left></span>
              <div class="wave-slider-box">
                <input type="range" min="0" max="100" value="50" class="wave-slider" data-slider>
                <span class="wave-value" data-slider-value>50</span>
              </div>
              <span class="wave-pole" data-pole-right></span>
            </div>
            <div class="wave-actions" data-slider-box>
              <button type="button" class="btn btn-primary" data-lock>Lock it in</button>
            </div>
            <p class="muted" data-giver-note hidden>You gave the clue — sit back and watch.</p>
            <p class="muted" data-lock-count></p>
          </section>

          <section data-view-reveal hidden></section>
          <section data-view-finished hidden></section>

          <div class="wave-board" data-board-wrap>
            <h4 class="section-title">Scores</h4>
            <div data-board></div>
          </div>
        </div>`;

      const q = (name) => root.querySelector(`[data-${name}]`);
      els = {
        progress: q("progress"),
        timer: q("timer"),
        clueText: q("clue-text"),
        clueGiver: q("clue-giver"),
        poleLeft: q("pole-left"),
        poleRight: q("pole-right"),
        slider: q("slider"),
        sliderValue: q("slider-value"),
        sliderBox: q("slider-box"),
        lockButton: q("lock"),
        giverNote: q("giver-note"),
        lockCount: q("lock-count"),
        board: q("board"),
        boardWrap: q("board-wrap"),
        views: {
          setup: q("view-setup"),
          clue: q("view-clue"),
          guess: q("view-guess"),
          reveal: q("view-reveal"),
          finished: q("view-finished"),
        },
      };

      els.slider.addEventListener("input", () => {
        localValue = Number(els.slider.value);
        els.sliderValue.textContent = localValue;
        sendMove(localValue, false);
      });
      els.slider.addEventListener("pointerdown", () => { dragging = true; });
      els.slider.addEventListener("pointerup", () => { dragging = false; });
      els.slider.addEventListener("blur", () => { dragging = false; });
      els.lockButton.addEventListener("click", () => {
        clearTimeout(moveTimer);
        sendMove(localValue, true);
      });

      ticker = setInterval(tick, 1000);
    },

    update(state) {
      const sub = state.sub;
      // Igra zna za igrača tek kad pošalje akciju, pa se javimo čim uđemo.
      if (!announced) {
        announced = true;
        api.sendAction({ type: "sync" });
      }
      endsAt = state.phase === "guess" && sub.ends_at ? new Date(sub.ends_at).getTime() : null;
      if (state.phase !== "guess") syncSent = false;
      tick();

      els.progress.textContent =
        state.phase === "setup" || state.phase === "finished"
          ? ""
          : `Turn ${state.turn} / ${state.total_turns}`;

      // Tablica se vidi cijelu igru osim na završnom ekranu, gdje je velika.
      const showBoard = state.phase !== "setup" && state.phase !== "finished";
      els.boardWrap.hidden = !showBoard;
      if (showBoard) els.board.replaceChildren(scoreboard(state.scoreboard));

      show(state.phase);
      if (state.phase === "setup") renderSetup(state);
      else if (state.phase === "clue") renderClue(state);
      else if (state.phase === "guess") renderGuess(state);
      else if (state.phase === "reveal") renderReveal(state);
      else if (state.phase === "finished") renderFinished(state);
    },

    unmount() {
      clearInterval(ticker);
      clearTimeout(moveTimer);
      root.innerHTML = "";
      els = {};
      endsAt = null;
      dragging = false;
      announced = false;
    },
  });
})();