"""Response models. They exist so the OpenAPI schema (and the generated TypeScript types)
describe what the server returns; routes declare them as their return annotation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Ok(BaseModel):
    ok: bool


class ProjectRef(BaseModel):
    name: str
    title: str


class ProjectList(BaseModel):
    projects: list[ProjectRef]


class ProjectName(BaseModel):
    name: str


class OutlineItemOut(BaseModel):
    id: int
    title: str
    type: str
    meta: dict[str, str]
    words: int
    children: list[OutlineItemOut]


class OutlineOut(BaseModel):
    title: str
    words: int
    chars: int
    items: list[OutlineItemOut]


class DocumentOut(BaseModel):
    id: int
    title: str
    text: str
    version: str
    words: int


class SavedOut(BaseModel):
    version: str
    words: int


class CharacterOut(BaseModel):
    id: int
    name: str
    importance: str
    pov: str
    motivation: str
    goal: str
    conflict: str
    epiphany: str
    summary_sentence: str
    summary_para: str
    summary_full: str
    notes: str
    color: str
    infos: list[tuple[str, str]]


class CharactersOut(BaseModel):
    characters: list[CharacterOut]


class LabelOut(BaseModel):
    name: str
    color: str


class LabelsAndStatusOut(BaseModel):
    labels: list[LabelOut]
    status: list[str]


class LabelsOut(BaseModel):
    labels: list[LabelOut]


class StatusOut(BaseModel):
    status: list[str]


class InfoAndSummaryOut(BaseModel):
    info: dict[str, str]
    summary: dict[str, str]


class InfoOut(BaseModel):
    info: dict[str, str]


class SummaryOut(BaseModel):
    summary: dict[str, str]


class StepOut(BaseModel):
    id: int
    name: str
    meta: str
    summary: str


class PlotOut(BaseModel):
    id: int
    name: str
    importance: str
    description: str
    result: str
    summary: str
    characters: list[int]
    steps: list[StepOut]


class PlotsOut(BaseModel):
    plots: list[PlotOut]


class WorldItemOut(BaseModel):
    id: int
    name: str
    description: str
    passion: str
    conflict: str
    children: list[WorldItemOut]


class WorldOut(BaseModel):
    items: list[WorldItemOut]


class SearchHit(BaseModel):
    kind: str
    id: int
    title: str
    matches: int
    snippets: list[str]


class SearchOut(BaseModel):
    query: str
    truncated: bool
    results: list[SearchHit]


class RevisionRef(BaseModel):
    timestamp: int
    words: int


class RevisionsOut(BaseModel):
    revisions: list[RevisionRef]


class RevisionOut(BaseModel):
    timestamp: int
    text: str


class RestoredOut(BaseModel):
    version: str
    text: str


class TrashedOut(BaseModel):
    ok: bool
    trashed_as: str


class RevisionRulesOut(BaseModel):
    keep: bool
    smartremove: bool
    rules: dict[str, float]


class SettingsOut(BaseModel):
    countSpaces: bool
    viewMode: str
    defaultTextType: str
    spell_dict: str = Field(alias="dict")
    revisions: RevisionRulesOut

    model_config = ConfigDict(populate_by_name=True)


class HealthOut(BaseModel):
    status: str
    version: str


class AuthStatusOut(BaseModel):
    setup_required: bool
    authenticated: bool
    totp_pending: bool


class LoginOut(BaseModel):
    ok: bool
    totp_required: bool


class TotpSetupOut(BaseModel):
    secret: str
    uri: str
    qr_svg_base64: str


class RecoveryCodesOut(BaseModel):
    ok: bool
    recovery_codes: list[str]


class MeOut(BaseModel):
    username: str
    totp_enabled: bool


class UserRef(BaseModel):
    id: int
    username: str
    totp_enabled: bool
    created_at: str


class UsersList(BaseModel):
    users: list[UserRef]


class SampleList(BaseModel):
    samples: list[str]


class TemplateList(BaseModel):
    templates: list[str]


class BacklinkOut(BaseModel):
    kind: str
    id: int
    title: str
    field: str
    count: int


class BacklinksOut(BaseModel):
    target_title: str
    backlinks: list[BacklinkOut]


class BrokenRefOut(BaseModel):
    source_kind: str
    source_id: int
    source_title: str
    field: str
    target_kind: str
    target_id: int


class BrokenRefsOut(BaseModel):
    broken: list[BrokenRefOut]


class WhiteboardViewport(BaseModel):
    x: float = 0.0
    y: float = 0.0
    zoom: float = 1.0


class WhiteboardBoard(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    nodes: list[dict] = Field(default_factory=list)
    edges: list[dict] = Field(default_factory=list)
    viewport: WhiteboardViewport = Field(default_factory=WhiteboardViewport)
    show_all_notes: bool = False


class WhiteboardsData(BaseModel):
    active_board_id: str = Field(min_length=1, max_length=100)
    boards: list[WhiteboardBoard] = Field(min_length=1)

