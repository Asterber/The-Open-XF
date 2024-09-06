from pydantic import ValidationError
from pywinauto import Application, WindowSpecification, keyboard
from pywinauto.controls.common_controls import (
    TreeViewWrapper,
    _listview_item,
    _treeview_element,
)
from pywinauto.controls.win32_controls import ComboBoxWrapper
from pywinauto.base_wrapper import ElementNotEnabled
from tqdm.auto import tqdm

from vc_parser import utils
from vc_parser.cache import Cache
from vc_parser.schemas import (
    ActionParam3DSound,
    ActionParamAsset,
    ActionParamCppFunction,
    ActionParamEnable,
    ActionParamInventory,
    ActionParamSetView,
    ActionParamStatement,
    ActionParamTimer,
    ActionParamUrl,
    Asset,
    Coordinates,
    DiscFile,
    Node,
    NodePath,
    RStyleFile,
    RStyleResource,
    RStyleText,
    Trigger,
    TriggerAction,
    Variable,
    AssetName,
)


def parse_assets(app: Application, cache: Cache) -> list[Asset]:
    res = []
    aw: WindowSpecification = app['Asset List']
    lv: WindowSpecification = aw["List View"]
    header = lv.header
    h_click = header.click
    h_click()
    items = lv.items()
    columns = lv.columns()
    pbar = tqdm(
        items[::len(columns)],
        desc="Parsing assets",
        total=int(len(items) / len(columns)),
    )
    items[0].click()
    ai = None
    for it in pbar:
        keyboard.send_keys('{ENTER}')
        if ai is None:
            ai = app['Asset Information']
        name = ai['NameEdit'].window_text().strip()
        if cache.assets.has_key(name):
            asset: Asset = cache.assets.get(name)[0]  # type: ignore
        else:
            description = ai["DescriptionEdit"].window_text()
            category = ai["CategoryCombobox"].window_text()
            db_id = ai["Db IDEdit"].window_text()
            a_type = ai["TypeCombobox"].window_text()
            resource_style = ai["StyleCombobox"].window_text()
            match resource_style:
                case "File":
                    disc_files = []
                    fbs = "Disc FileButton"
                    ai[fbs].click()
                    df = app["Disc Files"]
                    for j, disc in enumerate(
                        (
                            "Core Install",
                            "Min Install",
                            "Med Install",
                            "1",
                            "2",
                            "3",
                            "4",
                            "5",
                            "6",
                            "7",
                        )
                    ):
                        file_selector = disc + "Edit"
                        match disc:
                            case "Core Install":
                                start_selector = "StartEdit7"
                                end_selector = "EndEdit9"
                            case "Min Install":
                                start_selector = "StartEdit1"
                                end_selector = "EndEdit1"
                            case "Med Install":
                                start_selector = "StartEdit2"
                                end_selector = "EndEdit2"
                            case "5":
                                start_selector = "Edit20"
                                end_selector = "Edit21"
                            case "6":
                                start_selector = "Edit23"
                                end_selector = "Edit24"
                            case "7":
                                start_selector = "Edit26"
                                end_selector = "Edit27"
                            case _:
                                start_selector = f"StartEdit{j}"
                                end_selector = f"EndEdit{j}"
                        file = df[file_selector].window_text()
                        start = df[start_selector].window_text()
                        end = df[end_selector].window_text()
                        f = DiscFile(
                            disc=disc,
                            file=file,
                            start=start.strip() or None,
                            end=end.strip() or None,
                        )
                        disc_files.append(f)
                    keyboard.send_keys('{ESC}')
                    resource = RStyleFile(
                        file=ai["File(s)Edit1"].window_text(),
                        from_=ai["FromEdit1"].window_text(),
                        to=ai["ToEdit"].window_text(),
                        size_type=ai["ToComboBox2"].window_text(),
                        first_frame_only=ai[
                            "First Frame OnlyCheckBox"
                        ].get_check_state()
                        == 1,
                        loop=ai["LoopCheckBox"].get_check_state() == 1,
                        hotspots=ai["HotspotsCheckBox"].get_check_state() == 1,
                        status=ai["StatusComboBox"].window_text(),
                        disc_files=disc_files,
                    )
                case "Resource":
                    resource = RStyleResource(
                        id=ai["Resource IDEdit2"].window_text(),
                        type=ai["Resource TypeComboBox0"].window_text(),
                        status=ai["StatusComboBox"].window_text(),
                    )
                case "Text":
                    resource = RStyleText(
                        left=ai["LeftEdit2"].window_text(),
                        top=ai["TopEdit2"].window_text(),
                        right=ai["RightEdit"].window_text(),
                        bottom=ai["BottomEdit"].window_text(),
                        text=ai["TextEdit2"].window_text(),
                    )
                # case "Color":
                #     ...
                case _:
                    input(f"Not implemented for {resource_style=}")
                    ai.print_control_identifiers()
                    input(f"Not implemented for {resource_style=}")
                    raise Exception(f"Not implemented for {resource_style=}")
            asset = Asset(
                name=name,
                description=description,
                category=category,
                style=resource_style,
                type=a_type,
                db_id=db_id,
                resource=resource,
            )
            keyboard.send_keys('{ESC}')
            cache.assets.set(name, [asset])
            res.append(asset)
        keyboard.send_keys('{ESC}')
        h_click()
        keyboard.send_keys('{VK_DOWN}')
    return res


def parse_variable(window) -> Variable:
    name = window["NameEdit"].window_text().strip()
    vtype = window["ComboBox"].window_text()
    is_constant = window["ConstantCheckBox"].get_check_state() == 1
    match vtype:
        case "Boolean":
            initial_value = window["TrueRadioButton"].get_check_state() == 1
        case "Character" | "String":
            initial_value = window["Initial ValueEdit"].window_text()
        case "Integer":
            try:
                initial_value = int(window["Initial ValueEdit"].window_text())
            except ValueError:
                initial_value = (
                    "Incorrect value: " + window["Initial ValueEdit"].window_text()
                )
        case _:
            raise Exception(f"Not implement initial value for {vtype=}")
    return Variable(
        name=name, type=vtype, is_constant=is_constant, initial_value=initial_value
    )


def parse_trigger_action(app: Application, name: str) -> TriggerAction:
    w = app.window(title="Action")
    elements = [x for x in w.children() if isinstance(x, ComboBoxWrapper)]
    action_type = w["Action TypeComboBox"].window_text()
    try:
        match action_type:
            case "Enable":
                tree: TreeViewWrapper = w["TreeView"]
                selected = utils.get_selected_item(tree)
                params = ActionParamEnable(
                    action=w["Action CategoryComboBox"].window_text(),
                    path=selected.text(),
                )
            case "C++ Function":
                function = w["FunctionEdit2"].window_text()
                parameters = [x for x in w["ParametersListBox"].texts() if x]
                params = ActionParamCppFunction(
                    function=function, parameters=parameters
                )
            case "3D Sound":
                act = w["Action CategoryComboBox1"].window_text()
                if len(act) == 0:
                    act = None
                params = ActionParam3DSound(
                    action=act,
                    asset=w["Action TypeEdit3"].window_text(),
                    coordinates=Coordinates(
                        x=int(w["XEdit"].window_text()),
                        y=int(w["YEdit"].window_text()),
                    ),
                )
            case "Statement":
                params = ActionParamStatement(
                    exp1=w["Action CategoryEdit1"].window_text(),
                    op=w["Action TypeComboBox2"].window_text(),
                    exp2=w["Action TypeComboBox3"].window_text(),
                )
            case "Asset":
                act = w["Action CategoryComboBox1"].window_text()
                if len(act) == 0:
                    act = None
                asset = w["Action TypeEdit3"].window_text()
                if asset == "drag asset from asset list":
                    asset = None
                params = ActionParamAsset(
                    action=act,
                    asset=asset,
                )
            case "URL":
                params = ActionParamUrl(url=w["URLEdit"].window_text())
            case "Select Inventory" | "Deselect Inventory":
                params = ActionParamInventory(
                    item=w["Action CategoryComboBox1"].window_text()
                )
            case "Timer":
                params = ActionParamTimer(
                    action=w["Action CategoryComboBox1"].window_text(),
                    timer=w["Action CategoryComboBox2"].window_text(),
                    expires_ms=int(w["expires inEdit2"].window_text()),
                    is_periodic=w["PeriodicCheckBox"].get_check_state() == 1,
                )
            case "Set View":
                params = ActionParamSetView(
                    node=w["NodeComboBox"].window_text(),
                    location=w["LocationComboBox"].window_text(),
                    view_point=w["ViewPointComboBox"].window_text(),
                    view=w["ViewComboBox"].window_text(),
                )
            case _:
                w.print_control_identifiers()
                raise Exception(f"Not implement action params for {action_type=}")
    except ValidationError as e:
        w.print_control_identifiers()
        raise e
    ta = TriggerAction(
        name=name,
        exp1=w["IfEdit"].window_text(),
        op=w["Evaluate ExpressionComboBox"].window_text(),
        exp2=w["Evaluate ExpressionComboBox2"].window_text(),
        action=elements[-1].window_text(),
        action_type=action_type,
        action_params=params,
    )
    return ta


def parse_trigger(app, trigger_name: str, path: NodePath, cache: Cache) -> Trigger:
    if cache.trigger_actions.has_key(path):
        actions = cache.trigger_actions.get(path)
    else:
        actions = []
        w = app["Edit Trigger"]["ListBox"]
        eb = app["Edit Trigger"]["&EditButton"]
        texts = w.texts()
        for i in range(w.item_count()):
            w.select(i)
            eb.click()
            actions.append(parse_trigger_action(app, texts[i]))
            app["Action"]["Cancel"].click()
        cache.trigger_actions.set(path, actions)
    return Trigger(name=trigger_name, actions=actions)


def parse_asset_names(app: Application, path: NodePath, cache: Cache) -> list[Trigger]:
    if cache.asset_names.has_key(path):
        res = [x.name for x in cache.asset_names.get(path)]
    else:
        res = []
        if app["VC Authoring Tool -"][">>Button"].exists(1):
            try:
                b = app["VC Authoring Tool -"][">>Button"]
                if b.is_enabled():
                    for t in b.texts():
                        if t == ">>":
                            b.click()
                            c = "View Asset List"
                            w = app[c]
                            if not w["Ok"].exists(1):
                                c = "Floorplan Asset List"
                                w = app[c]
                            w = w["ListBox"]
                            res += [x for x in w.texts() if x]
                            app[c]["Ok"].click()
                            break
            except ElementNotEnabled:
                ...
        cache.asset_names.set(path, [AssetName(name=x) for x in res])
    return res


def parse_triggers(app: Application, path: NodePath, cache: Cache) -> list[Trigger]:
    if cache.triggers.has_key(path):
        res = cache.triggers.get(path)
    else:
        res = []
        app["VC Authoring Tool -"]["Triggers"].click()
        w = app["Triggers"]["ListBox"]
        texts = w.item_texts()
        for i in range(w.item_count()):
            w.select(i)
            app["Triggers"]["Edit"].click()
            res.append(parse_trigger(app, texts[i], path + f"_{i}_{texts[i]}", cache))
            app["Edit Trigger"]["OK"].click()
        app["Triggers"]["Cancel"].click()
        cache.triggers.set(path, res)
    return res


def parse_variables(app: Application, path: NodePath, cache: Cache) -> list[Variable]:
    if cache.variables.has_key(path):
        res = cache.variables.get(path)
    else:
        res = []
        app["VC Authoring Tool -"]["Variables"].click()
        w = app["Variables"]["ListBox"]
        for i in range(w.item_count()):
            w.select(i)
            app["Variables"]["Edit"].click()
            res.append(parse_variable(app["Edit Variable"]))
            app["Edit Variable"]["Cancel"].click()
        app["Variables"]["Cancel"].click()
        cache.variables.set(path, res)
    return res


def open_all_nodes(node):
    """Open all nodes on main nodes view in the app"""
    elements = [node, *node.sub_elements()]
    for element in elements:
        element: _treeview_element = element
        element.select()


def parse_nodes(
    app,
    node: _treeview_element,
    cache: Cache,
    prev_path: None | NodePath = None,
    is_first: bool = False,
) -> Node:
    node_text = node.text()
    node.select()
    if prev_path is None:
        path = [
            node_text,
        ]
    else:
        path = [prev_path, node_text]
    path = "/".join(path)

    # Need because sometimes right window not updated after tree node select called
    if is_first:
        keyboard.send_keys("{VK_DOWN}{VK_UP}")
    else:
        keyboard.send_keys("{VK_UP}{VK_DOWN}")

    name = app["VC Authoring Tool -"]["NameEdit"].window_text()
    if node_text != "X-Files" and name != node_text:
        raise Exception(
            f"Parsing node with text '{node_text}' != right window title '{name}'"
        )
    n = Node(name=node.text(), path=path)
    n.asset_names = parse_asset_names(app, path, cache)
    n.variables = parse_variables(app, path, cache)
    n.triggers = parse_triggers(app, path, cache)
    childrens = node.children()
    n.childrens = [
        parse_nodes(app, child, prev_path=path, cache=cache) for child in childrens
    ]
    return n
