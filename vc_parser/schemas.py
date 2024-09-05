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


class Node(BaseModel):
    name: str
    childrens: list[Self] = Field(default_factory=list)
    variables: list[Variable] = Field(default_factory=list)
    triggers: list[Trigger] = Field(default_factory=list)
    path: NodePath
    asset_names: list[str] = Field(default_factory=list)

    def _print(self, indent: int):
        print(" " * indent + ">", self.name)
        for c in self.childrens:
            c._print(indent + 1)

    def print_tree(self):
        self._print(indent=0)


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
    start: int
    end: int


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
