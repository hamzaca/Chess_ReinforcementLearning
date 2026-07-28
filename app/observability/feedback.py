"""Placeholder for user-feedback collection.

Planned: endpoint + table letting users rate agent moves ("good move /
blunder"), producing labeled data for the future RL reward model.
"""


class FeedbackCollector:  # pragma: no cover - placeholder
    def record(self, game_id: int, move_number: int, rating: int, comment: str = "") -> None:
        raise NotImplementedError("Feedback collection is not implemented yet.")
