import time

from pydantic import ValidationError
from pywinauto import Application, WindowSpecification, keyboard
from pywinauto.base_wrapper import ElementNotEnabled
from pywinauto.controls.common_controls import (
    TreeViewWrapper,
    _treeview_element,
)
from pywinauto.controls.win32_controls import ComboBoxWrapper
from tqdm.auto import tqdm

from vc_parser import utils
from vc_parser.cache import Cache
from vc_parser.schemas import (
    ActionParam3DSound,
    ActionParamAsset,
    ActionParamCppFunction,
    ActionParamEnable,
    ActionParamInterface,
    ActionParamInventory,
    ActionParamSetView,
    ActionParamStatement,
    ActionParamTimer,
    ActionParamUrl,
    Asset,
    AssetName,
    Character,
    CharacterProperties,
    Conversation,
    Coordinates,
    DestinationView,
    DiscFile,
    ExplorationProperties,
    HotSpot,
    IdeaResponse,
    Navigation,
    Node,
    NodePath,
    RStyleFile,
    RStyleResource,
    RStyleText,
    Trigger,
    TriggerAction,
    Variable,
    ViewNavigation,
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
            case "Interface":
                params = ActionParamInterface(
                    action=w['Action CategoryComboBox1'].window_text(),
                    interface=w['TypeComboBox6'].window_text(),
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


def parse_trigger(app, trigger_name: str, path: NodePath, cache: Cache | None) -> Trigger:
    if cache is not None and cache.trigger_actions.has_key(path):
        actions = cache.trigger_actions.get(path)
    else:
        actions = []
        w = app["Edit Trigger"]["ListBox"]
        eb = app["Edit Trigger"]["&EditButton"]
        texts = w.item_texts()
        for i in range(w.item_count()):
            w.select(i)
            eb.click()
            while not app.window(title="Action").exists():
                eb.click()
            actions.append(parse_trigger_action(app, texts[i]))
            app["Action"]["Cancel"].click()
        if cache is not None:
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


def parse_triggers(app: Application, path: NodePath, cache: Cache | None) -> list[Trigger]:
    if cache is not None and cache.triggers.has_key(path):
        res = cache.triggers.get(path)
    else:
        res = []
        app["VC Authoring Tool -"]["Triggers"].click()
        w = app["Triggers"]["ListBox"]
        texts = w.item_texts()
        for i in range(w.item_count()):
            w.select(i)
            app["Triggers"]["Edit"].click()
            while not app.windows(title="Trigger"):
                app["Triggers"]["Edit"].click()
            res.append(parse_trigger(app, texts[i], path + f"_{i}_{texts[i]}", cache))
            app["Edit Trigger"]["OK"].click()
        app["Triggers"]["Cancel"].click()
        if cache is not None:
            cache.triggers.set(path, res)
    return res


def parse_variables(app: Application, path: NodePath, cache: Cache | None, from_conversation: bool = False) -> list[Variable]:
    if cache is not None and cache.variables.has_key(path):
        res = cache.variables.get(path)
    else:
        res = []
        if not from_conversation:
            app["VC Authoring Tool -"]["Variables"].click()
            w = app["Variables"]["ListBox"]
            edit_btn = app["Variables"]["Edit"]
        else:
            tw = app.top_window()
            w = tw['VariablesListBox']
            edit_btn = tw['EditButton']
        for i in range(w.item_count()):
            w.select(i)
            edit_btn.click()
            while not app.windows(title="Edit Variable"):
                edit_btn.click()
            res.append(parse_variable(app["Edit Variable"]))
            app["Edit Variable"]["Cancel"].click()
        app["Variables"]["Cancel"].click()
        if cache is not None:
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
    app_uia,
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
    maybe_has_navigations = app["VC Authoring Tool -"][">>Button"].exists(1) and app["VC Authoring Tool -"][">>Button"].is_enabled() and any([x == '>>' for x in app["VC Authoring Tool -"][">>Button"].texts()])
    print(path, maybe_has_navigations)
    if maybe_has_navigations and 'X-Files/Node 1: Setup/' in path:
        n.view_navigation = parse_navigations(app, path, cache)
        
    childrens = node.children()
    n.childrens = [
        parse_nodes(app, app_uia, child, prev_path=path, cache=cache) for child in childrens
    ]
    return n
def wait_window_or_ctrl_c(app: Application, titles: str) -> str | None:
    '''
    Function waiting for window of any title appears
    return: finded title or None if ctrl+c pressed
    '''
    try:
        while True:
            for title in titles:
                ws = app.windows(title=title)
                if len(ws):
                    return title
            time.sleep(0.1)
    except KeyboardInterrupt:
        return None

def parse_hot_spot_properties(elements: list) -> HotSpot:
    cs = elements
    name = cs[1].texts()[cs[1].selected_index() + 1]
    cursor = cs[2].texts()[cs[2].selected_index() + 1]
    left, top, right, bottom = cs[3].texts()[0], cs[4].texts()[0], cs[5].texts()[0], cs[6].texts()[0]
    return HotSpot(name=name, cursor=cursor, left=left, top=top, right=right, bottom=bottom)

def parse_enabled_and_db_id_properties(elements: list) -> tuple[str | None, str]:
    cs = elements
    enabled = None
    if cs[1].get_check_state() == 1:
        enabled = "Always Enabled"
    elif cs[2].get_check_state() == 1:
        enabled = "Initially Enabled"
    elif cs[3].get_check_state() == 1:
        enabled = "Initially Disabled"
    db_id = cs[6].texts()[0]
    return enabled, db_id

def parse_variables_properties(elements: list, app: Application) -> None:
    variables = []
    variables_count = elements[6].item_count()
    texts = elements[6].item_texts()
    assert len(texts) == variables_count
    edit_button = elements[2]
    for i in range(variables_count):
        elements[6].select(i)
        edit_button.click()
        variables.append(parse_variable(app['Edit Variable']))
    if variables_count:
        keyboard.send_keys('{ESC}')
    return variables

def parse_destination_view_properties(elements: list) -> DestinationView:
    cs = elements
    node_name, location = cs[1].texts()[0], cs[2].texts()[0]
    viewpoint, view = cs[3].texts()[0], cs[4].texts()[0]
    destination_view = DestinationView(node=node_name, location=location, viewpoint=viewpoint, view=view)
    return destination_view

def parse_triggers_properties(elements: list, app: Application) -> None:
    triggers = []
    triggers_count = elements[6].item_count()
    texts = elements[6].item_texts()
    assert len(texts) == triggers_count
    edit_button = elements[2]
    for i in range(triggers_count):
        elements[6].select(i)
        edit_button.click()
        triggers.append(parse_trigger(app, texts[i], '', None))
        app.windows(title='Trigger')[0].children()[6].click()
    return triggers

def parse_conversation(app, conversation_name: str) -> Conversation:
    ws = app['Edit Conversation']
    name = ws['NameEdit'].window_text()
    dialogs = []
    dlg_btn = ws['>>Button1']
    if dlg_btn.is_enabled():
        dlg_btn.click()
        dw = app['Dialog Asset List']
        dialogs = dw['ListBox'].item_texts()
        dw['OKButton'].click()

    questions = []
    q_btn = ws['>>Button2']
    if q_btn.is_enabled():
        q_btn.click()
        dw = app['Question Asset List']
        questions = dw['ListBox'].item_texts()
        dw['OKButton'].click()

    replies = []
    replies_btn = ws['>>Button3']
    if replies_btn.is_enabled():
        replies_btn.click()
        dw = app['Reply Asset List']
        replies = dw['ListBox'].item_texts()
        dw['OKButton'].click()

    atoms = []
    atoms_btn = ws['>>Button4']
    if atoms_btn.is_enabled():
        atoms_btn.click()
        dw = app['Atom Asset List']
        atoms = dw['ListBox'].item_texts()
        dw['OKButton'].click()

    support_history = ws['HistoryGroupBox'].get_check_state() == 1

    ws['&VariablesButton'].click()
    variables = parse_variables(app, '', None, True)

    ws['&TriggersButton'].click()
    triggers = parse_triggers(app, "", None)
    if app['Trigger List']['CancelButton'].exists():
        app['Trigger List']['CancelButton'].click()

    ws['&EnabledButton'].click()
    while not app.windows(title="Enabled"):
        ws['&EnabledButton'].click()
    enabled, db_id = parse_enabled_and_db_id_properties(app.windows(title="Enabled")[0].children()[1:])
    app['Enabled']['CancelButton'].click()
    while app.top_window().window_text() == 'Edit Conversation':
        app['Edit Conversation']['CancelButton'].click()

    res = Conversation(name=name, dialogs=dialogs, questions=questions, replies=replies, atoms=atoms, support_history=support_history, variables=variables, triggers=triggers, enabled=enabled, db_id=db_id)
    return res

def parse_conversation_properties(elements: list, app: Application) -> None:
    conversations = []
    conversations_count = elements[6].item_count()
    texts = elements[6].item_texts()
    assert len(texts) == conversations_count
    edit_button = elements[2]
    for i in range(conversations_count):
        elements[6].select(i)
        edit_button.click()
        conversations.append(parse_conversation(app, texts[i],))
    while app.top_window().window_text() != 'Character Properties':
        app.top_window()['CancelButton'].click()
    return conversations


def parse_character_properties(elements: list) -> Character:
    cs = elements
    name = cs[1].item_texts()[cs[1].selected_index()]
    description = cs[2].texts()[0]
    db_id = cs[6].texts()[0]
    return Character(name=name, description=description, db_id=db_id)

def parse_idea_response(app: Application, name: str) -> IdeaResponse:
    w = app.window(title='Edit Idea Response')
    idea_icon = w['Idea IconComboBox'].window_text()
    questions = []
    q_btn = w['>>2']
    if q_btn.is_enabled():
        q_btn.click()
        questions = app.window(title='Question Asset List')['ListBox'].item_texts()
        app.window(title='Question Asset List')['OkButton'].click()

    replies = []
    r_btn = w['>>Button1']
    if r_btn.is_enabled():
        r_btn.click()
        replies = app.window(title='Reply Asset List')['ListBox'].item_texts()
        app.window(title='Reply Asset List')['OkButton'].click()

    atoms = []
    a_btn = w['>>3']
    if a_btn.is_enabled():
        a_btn.click()
        atoms = app.window(title='Atom Asset List')['ListBox'].item_texts()
        app.window(title='Atom Asset List')['OkButton'].click()

    w['&VariablesButton'].click()
    variables = parse_variables(app, '', None, True)

    w['&TriggersButton'].click()
    triggers = parse_triggers(app, "", None)
    if app['Trigger List']['CancelButton'].exists():
        app['Trigger List']['CancelButton'].click()

    while app.top_window().window_text() == 'Edit Idea Response':
        app['Edit Idea Response']['OkButton'].click()
    return IdeaResponse(
        name=name,
        idea_icon=idea_icon,
        questions=questions,
        replies=replies,
        atoms=atoms,
        variables=variables,
        triggers=triggers,
    )


def parse_idea_response_properties(elements: list, app: Application) -> None:
    idea_responses = []
    idea_responses_count = elements[6].item_count()
    texts = elements[6].item_texts()
    assert len(texts) == idea_responses_count
    edit_button = elements[2]
    for i in range(idea_responses_count):
        elements[6].select(i)
        edit_button.click()
        idea_responses.append(parse_idea_response(app, texts[i]))
    return idea_responses

def parse_acknowledgements_properties(elements: list) -> list[str]:
    acknowledgements = elements[5].item_texts()
    return acknowledgements

def parse_navigations(app: Application, path: str, cache: Cache) -> ViewNavigation:
    if cache.view_navigation.has_key(path):
        return cache.view_navigation.get(path)[0]
    app["VC Authoring Tool -"].menu_select(r"View -> Screen View")
    navigations = []
    character_properties = []
    explorable_properties = []
    titles = ['Navigation Properties', 'Explorable Properties', 'Character Properties']
    print(f"{path=}")
    print("Please select all boxes for Navigation, Explorable and Character. Then press Ctrl+C for continue")
    while title := wait_window_or_ctrl_c(app, titles):
        print(f"Found {title=}")
        w = app.windows(title=title)[0]
        cs = w.children()
        tab_control = cs[-1]
        if title == titles[0]:
            hot_spot = parse_hot_spot_properties(cs)

            tab_control.select(1)
            cs = w.children()
            destination_view = parse_destination_view_properties(cs)

            tab_control.select(2)
            cs = w.children()
            variables = parse_variables_properties(cs, app)

            tab_control.select(3)
            cs = w.children()
            triggers = parse_triggers_properties(cs, app)

            tab_control.select(4)
            cs = w.children()
            enabled, db_id = parse_enabled_and_db_id_properties(cs)
            nav = Navigation(
                    hot_spot=hot_spot,
                    destination_view=destination_view,
                    enabled=enabled,
                    db_id=db_id,
                )
            if nav not in navigations:
                navigations.append(nav)
            else:
                print("This nav already added")
        elif title == titles[1]:
            hot_spot = parse_hot_spot_properties(cs)
            
            tab_control.select(1)
            cs = w.children()
            variables = parse_variables_properties(cs, app)

            tab_control.select(2)
            cs = w.children()
            triggers = parse_triggers_properties(cs, app)

            tab_control.select(3)
            cs = w.children()
            enabled, db_id = parse_enabled_and_db_id_properties(cs)

            exp = ExplorationProperties(hot_spot=hot_spot, variable=variables, triggers=triggers, enabled=enabled, db_id=db_id)
            if exp not in explorable_properties:
                explorable_properties.append(exp)
            else:
                print("This exp already added")
        elif title == titles[2]:
            character = parse_character_properties(cs)

            tab_control.select(1)
            cs = w.children()
            hot_spot = parse_hot_spot_properties(cs)

            tab_control.select(2)
            cs = w.children()
            conversations = parse_conversation_properties(cs, app)

            tab_control.select(3)
            cs = w.children()
            idea_responses = parse_idea_response_properties(cs, app)

            tab_control.select(4)
            cs = w.children()
            acknowledgements = parse_acknowledgements_properties(cs)

            tab_control.select(5)
            cs = w.children()
            variables = parse_variables_properties(cs, app)

            tab_control.select(6)
            cs = w.children()
            triggers = parse_triggers_properties(cs, app)

            tab_control.select(7)
            cs = w.children()
            enabled, db_id = parse_enabled_and_db_id_properties(cs)

            cp = CharacterProperties(character=character, hot_spot=hot_spot, conversations=conversations, idea_responses=idea_responses, acknowledgements=acknowledgements, variables=variables, triggers=triggers)
            if cp not in character_properties:
                character_properties.append(cp)
            else:
                print("This cp already added")
        while not app.top_window().window_text().startswith('Current View -'):
            keyboard.send_keys('{ESC}')
        print(f"{len(navigations)=}")
        print(f"{len(explorable_properties)=}")
        print(f"{len(character_properties)=}")
    res = ViewNavigation(navigations=navigations, explorations=explorable_properties, characters=character_properties)
    cache.view_navigation.set(path, [res])
    app["VC Authoring Tool -"].menu_select(r"View -> Screen View")
    return res
