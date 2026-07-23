from dataclasses import dataclass


@dataclass
class Category:
    name: str
    position: int = 0
    # Protected categories (Savings, Other) carry meaning the reporting layer
    # depends on, so the management UI forbids renaming or deleting them.
    is_protected: bool = False
    id: int | None = None
