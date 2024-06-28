from dataclasses import dataclass, field


@dataclass
class Text:
    widget_type: str = "text"
    text: str = ""


@dataclass
class NoteText:
    widget_type: str = "note_text"
    text: str = ""


@dataclass
class List:
    widget_type: str = "list"
    items: list[str] = field(default_factory=list)
    ordered: bool = False


@dataclass
class FormSpecWrapper:
    id: str
    widget_type: str = "form_spec"
    definition: object | None = None
