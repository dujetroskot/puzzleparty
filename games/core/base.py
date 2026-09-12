from abc import ABC, abstractmethod


class GameError(Exception):
    """Akcija nije dozvoljena. Poruka ide samo igraču koji ju je poslao."""


class GameMode(ABC):
    # Metapodaci za lobby. Svaka igra ih postavlja.
    game_type = ""       # jedinstveni ID, npr. "movie"
    name = ""
    emoji = ""
    description = ""
    client_script = ""   # JS file unutar static/, npr. "js/games/movie.js"

    @abstractmethod
    def create_state(self):
        """Vrati početni PUNI state nove runde. Smije sadržavati tajne."""

    @abstractmethod
    def handle_action(self, state, action, player):
        """Primijeni akciju i vrati novi state. Za neispravnu akciju baci GameError.

        player je dict {"id": ..., "nickname": ...}.
        """

    @abstractmethod
    def get_public_state(self, state, viewer):
        """Vrati SAMO ono što ovaj igrač smije vidjeti.

        viewer je dict {"id": ..., "nickname": ...}. Igre kod kojih svi vide
        isto ga jednostavno ignoriraju.
        """
    @abstractmethod
    def is_solved(self, state):
        """Je li zagonetka riješena."""