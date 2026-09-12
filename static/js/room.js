(() => {
  "use strict";

  // Registry frontend dijela igara. Svaki game JS poziva PuzzleGames.register().
  // Igra mora imati: mount(rootElement, api), update(publicState), unmount().
  const games = {};
  window.PuzzleGames = {
    register(type, impl) {
      games[type] = impl;
    },
  };

  const config = JSON.parse(document.getElementById("room-config").textContent);
  const $ = (id) => document.getElementById(id);

  let socket = null;
  let current = null; // { type, impl }
  let errorTimer = null;

  function send(message) {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(message));
    }
  }

  // Jedino što igre smiju: poslati akciju serveru.
  const api = {
    sendAction: (action) => send({ type: "action", action }),
  };

  function setStatus(text, className) {
    const el = $("connection-status");
    el.textContent = text;
    el.className = `status ${className}`;
  }

  function showError(message) {
    const el = $("room-error");
    el.textContent = message;
    el.hidden = false;
    clearTimeout(errorTimer);
    errorTimer = setTimeout(() => { el.hidden = true; }, 3000);
  }

  // Zamjena za confirm(): vrati Promise koji se riješi s true/false.
  // Za razliku od confirm(), ne blokira JS, pa state i dalje stiže dok je otvoren.
  function confirmDialog(message, okLabel = "Confirm") {
    return new Promise((resolve) => {
      const modal = $("modal");
      $("modal-text").textContent = message;
      $("modal-ok").textContent = okLabel;
      modal.hidden = false;

      const close = (answer) => {
        modal.hidden = true;
        $("modal-ok").removeEventListener("click", onOk);
        $("modal-cancel").removeEventListener("click", onCancel);
        modal.removeEventListener("click", onBackdrop);
        document.removeEventListener("keydown", onKey);
        resolve(answer);
      };
      const onOk = () => close(true);
      const onCancel = () => close(false);
      const onBackdrop = (event) => {
        if (event.target === modal) close(false);
      };
      const onKey = (event) => {
        if (event.key === "Escape") close(false);
      };

      $("modal-ok").addEventListener("click", onOk);
      $("modal-cancel").addEventListener("click", onCancel);
      modal.addEventListener("click", onBackdrop);
      document.addEventListener("keydown", onKey);
      $("modal-ok").focus();
    });
  }

  function renderPlayers(players) {
    const items = players.map((player) => {
      const li = document.createElement("li");
      li.className = "player" + (player.id === config.me ? " is-me" : "");
      li.textContent = player.nickname; // textContent, nikad innerHTML za korisnički tekst
      return li;
    });
    $("player-list").replaceChildren(...items);
  }

  function renderGame(game) {
    if (!game) {
      if (current) current.impl.unmount();
      current = null;
      $("game-view").hidden = true;
      $("lobby-view").hidden = false;
      $("share-row").hidden = false;
      document.querySelector(".container").classList.remove("wide");
      return;
    }

    const impl = games[game.type];
    if (!impl) {
      showError(`Missing frontend for game "${game.type}".`);
      return;
    }

    if (!current || current.type !== game.type) {
      if (current) current.impl.unmount();
      impl.mount($("game-root"), api);
      current = { type: game.type, impl };
    }

    $("lobby-view").hidden = true;
    $("game-view").hidden = false;
    $("share-row").hidden = true;
    document.querySelector(".container").classList.toggle("wide", game.type === "country");
    $("game-title").textContent = `${game.emoji} ${game.name}`;
    $("game-solved").hidden = !game.solved;
    impl.update(game.state);
  }

  function handleMessage(message) {
    if (message.type === "state") {
      renderPlayers(message.players);
      renderGame(message.game);
    } else if (message.type === "error") {
      showError(message.message);
    }
  }

  function connect() {
    const scheme = location.protocol === "https:" ? "wss" : "ws";
    socket = new WebSocket(`${scheme}://${location.host}/ws/room/${config.code}/`);
    setStatus("Connecting…", "status-connecting");

    socket.addEventListener("open", () => setStatus("Live", "status-live"));
    socket.addEventListener("message", (event) => handleMessage(JSON.parse(event.data)));
    socket.addEventListener("close", (event) => {
      if (event.code === 4003) {
        // Server nas ne prepoznaje kao igrača. Reload vodi na unos nicknamea.
        location.reload();
        return;
      }
      setStatus("Reconnecting…", "status-connecting");
      setTimeout(connect, 1500);
    });
  }

  document.querySelectorAll("[data-game-type]").forEach((button) => {
    button.addEventListener("click", () =>
      send({ type: "start_game", game_type: button.dataset.gameType })
    );
  });

  $("back-to-lobby").addEventListener("click", async () => {
    if (await confirmDialog("Leave this game for everyone?", "Leave")) {
      send({ type: "end_game" });
    }
  });

  $("new-round").addEventListener("click", async () => {
    if (current && (await confirmDialog("Start a new round for everyone?", "New round"))) {
      send({ type: "start_game", game_type: current.type });
    }
  });

  $("copy-link").addEventListener("click", async (event) => {
    const input = $("room-link");
    try {
      await navigator.clipboard.writeText(input.value);
      event.target.textContent = "Copied!";
    } catch {
      input.select();
    }
  });

  // Spajamo se tek kad su učitani i JS fileovi svih igara.
  document.addEventListener("DOMContentLoaded", connect);
})();