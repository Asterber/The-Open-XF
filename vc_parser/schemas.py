from typing import Literal, Self

from pydantic import BaseModel, Field

NodePath = str
VariableType = Literal["Integer", "Character", "Boolean", "String"]
Operator = Literal[
    "=", "!=", ">", "<", ">=", "<=", "and", "or", "++", "+=", "-=", "*=", "/=", "%="
]
Action = Literal["Standard", "Game", "Inventory", "Interface"]
ActionType = Literal[
    "Statement",
    "Asset",
    "Timer",
    "Select Inventory",
    "Deselect Inventory",
    "Enable",
    "Set View",
    "C++ Function",
    "3D Sound",
    "URL",
    "Interface",
]


class Coordinates(BaseModel):
    x: int
    y: int


class ActionParamStatement(BaseModel):
    exp1: str
    op: Operator
    exp2: str


class ActionParamUrl(BaseModel):
    url: str


class ActionParamInventory(BaseModel):
    item: str


class ActionParamInterface(BaseModel):
    action: str
    interface: str

class ActionParamSetView(BaseModel):
    node: str
    location: str
    view_point: str
    view: str


class ActionParamTimer(BaseModel):
    action: Literal["Start", "Stop"]
    timer: str
    expires_ms: int
    is_periodic: bool


class ActionParamAsset(BaseModel):
    action: (
        Literal[
            "Preload",
            "Play/Display (once)",
            "Play/Display (loop)",
            "Stop/Unshow",
            "Unload",
        ]
        | None
    )
    asset: str | None


class ActionParam3DSound(ActionParamAsset):
    coordinates: Coordinates


class ActionParamCppFunction(BaseModel):
    function: str
    parameters: list[str]


class ActionParamEnable(BaseModel):
    action: Literal["Enable", "Disable"]
    path: str


ActionParams = (
    ActionParam3DSound
    | ActionParamAsset
    | ActionParamEnable
    | ActionParamCppFunction
    | ActionParamStatement
    | ActionParamUrl
    | ActionParamInventory
    | ActionParamTimer
    | ActionParamSetView
    | ActionParamInterface
)


class TriggerAction(BaseModel):
    name: str
    exp1: str
    op: Operator
    exp2: str
    action: Action
    action_type: ActionType
    action_params: ActionParams


class Trigger(BaseModel):
    name: str
    actions: list[TriggerAction]


class Variable(BaseModel):
    name: str
    type: VariableType
    is_constant: bool
    initial_value: str | bool | int


AssetStyle = Literal[
    "File",
    "Resource",
    "Text",
    "Color",
]
ResourceType = Literal[
    "Cursor",
    "Icon",
    "Bitmap",
    "String",
    "Font",
]
ResourceStatus = Literal[
    "Placeholder",
    "Final",
]


class DiscFile(BaseModel):
    disc: str
    file: str
    start: int | None
    end: int | None


class RStyleResource(BaseModel):
    id: int
    type: ResourceType
    status: ResourceStatus


class RStyleFile(BaseModel):
    file: str
    from_: int
    to: int
    size_type: Literal["mS", "Seconds", "Frames"]
    first_frame_only: bool
    loop: bool
    hotspots: bool
    status: ResourceStatus
    disc_files: list[DiscFile]


class RStyleText(BaseModel):
    left: int
    top: int
    right: int
    bottom: int
    text: str


RStyle = RStyleResource | RStyleFile | RStyleText


class Asset(BaseModel):
    name: str
    description: str | None
    category: str
    style: AssetStyle
    type: str
    resource: RStyle
    db_id: int


class AssetName(BaseModel):
    name: str

Cursor = Literal['Left', 'Right', 'Forward', 'Back', 'Up', 'Ups', 'Down', 'Gunsight', 'ViewFinder', 'Eye', 'ActionFist', 'X', 'InventoryBadge', 'InventoryCaseFiles', 'InventoryCowbar', 'Inventory',]

class HotSpot(BaseModel):
    name: Literal['Default Left', 'Default Right', 'Default Forward', 'Default Down', 'Default Up', 'CU', 'Back', 'Custom']
    cursor: str
    left: int
    top: int
    right: int
    bottom: int

class DestinationView(BaseModel):
    node: str
    location: str
    viewpoint: str
    view: str

class Navigation(BaseModel):
    hot_spot: HotSpot
    destination_view: DestinationView
    enabled: str
    db_id: int

class Character(BaseModel):
    name: str
    description: str
    db_id: int


class CharacterProperties(BaseModel):
    character: Character
    hot_spot: HotSpot
    conversations: list
    idea_responses: list
    acknowledgements: list
    variables: list
    triggers: list[Trigger]

class ExplorationProperties(BaseModel):
    hot_spot: HotSpot
    variable: list
    triggers: list[Trigger]
    enabled: str
    db_id: int

class ViewNavigation(BaseModel):
    navigations: list[Navigation]
    explorations: list[ExplorationProperties]
    characters: list[CharacterProperties]


class Conversation(BaseModel):
    name: str
    dialogs: list[str]
    questions: list[str]
    replies: list[str]
    atoms: list[str]
    support_history: bool
    variables: list[Variable]
    triggers: list[Trigger]
    enabled: str
    db_id: int

class IdeaResponse(BaseModel):
    name: str
    idea_icon: str
    questions: list[str]
    replies: list[str]
    atoms: list[str]
    variables: list[Variable]
    triggers: list[Trigger]

class Node(BaseModel):
    name: str
    childrens: list[Self] = Field(default_factory=list)
    variables: list[Variable] = Field(default_factory=list)
    triggers: list[Trigger] = Field(default_factory=list)
    path: NodePath
    asset_names: list[str] = Field(default_factory=list)
    view_navigation: ViewNavigation | None = None

    def _print(self, indent: int):
        print(" " * indent + ">", self.name)
        for c in self.childrens:
            c._print(indent + 1)

    def print_tree(self):
        self._print(indent=0)

    @staticmethod
    def find_node(root_node: "Node", path: str) -> "Node":
        n = root_node
        for p in path.split("/")[1:]:
            p = p.strip()
            c = [x for x in n.childrens if x.name.strip() == p]
            if len(c) == 0:
                raise Exception(f"Not found path {path}")
            if len(c) > 1:
                raise Exception(f"Find multiple nodes for {path}")
            n = c[0]
        return n

