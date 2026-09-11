PuzzleGames.register("demo", {
  mount(root, api) {
    root.innerHTML = `
      <div class="demo">
        <p class="muted">Click together until you hit the secret number (5–15).</p>
        <div class="demo-count" data-count>0</div>
        <p class="muted" data-info></p>
        <button type="button" class="btn btn-primary" data-increment>+1</button>
      </div>`;
    this.root = root;
    this.els = {
      count: root.querySelector("[data-count]"),
      info: root.querySelector("[data-info]"),
      button: root.querySelector("[data-increment]"),
    };
    this.els.button.addEventListener("click", () => api.sendAction({ type: "increment" }));
  },

  update(state) {
    const solved = state.secret !== undefined;
    this.els.count.textContent = state.count;
    this.els.button.disabled = solved;
    if (solved) {
      this.els.info.textContent = `The secret number was ${state.secret}.`;
    } else if (state.last_player) {
      this.els.info.textContent = `Last click: ${state.last_player}`;
    } else {
      this.els.info.textContent = "";
    }
  },

  unmount() {
    this.root.innerHTML = "";
  },
});