import argparse
import json
import logging
import os
from enum import Enum

from pydantic import BaseModel
from pywinauto import WindowSpecification
from pywinauto.application import Application
from pywinauto.controls.common_controls import _treeview_element

from vc_parser.cache import Cache, FileCache
from vc_parser.parsing import open_all_nodes, parse_assets, parse_nodes
from vc_parser.schemas import (
    Asset,
    AssetName,
    Trigger,
    TriggerAction,
    Variable,
    ViewNavigation,
)

logger = logging.getLogger("parser")


class WhatParse(Enum):
    NODES = "NODES"
    ASSETS = "ASSETS"


class Config(BaseModel):
    game_path: str
    output_file_name: str
    vc_exe_name: str
    debug: bool
    just_open: bool
    what_parse: WhatParse


def parse_config_from_args() -> Config:
    parser = argparse.ArgumentParser(
        description="Program parse .hdb file of The X-Files game into needed structures"
    )
    parser.add_argument("-d", type=str, help="Path with installed game")
    parser.add_argument(
        "-o", type=str, help="Output file name. Default tree.json", default="tree.json"
    )
    parser.add_argument(
        "-e",
        type=str,
        help="VC executable name which locate in path with installed game. Default 'vc author 4.0.exe'",
        default="vc author 4.0.exe",
    )
    parser.add_argument(
        "--debug",
        type=bool,
        help="Enable debug: don't close application window until press enter. Default False",
        default=False,
    )
    parser.add_argument(
        "-jo",
        type=bool,
        help="Just open application and exit program. Default False",
        default=False,
    )
    parser.add_argument(
        "-p",
        type=str,
        help="What kind of parse use. NODES or ASSETS. Default ASSETS",
        default=WhatParse.ASSETS,
    )
    args = vars(parser.parse_args())
    return Config(
        game_path=args["d"],
        output_file_name=args["o"],
        vc_exe_name=args["e"],
        debug=args["debug"],
        just_open=args["jo"],
        what_parse=args["p"],
    )


def start_app(game_path: str, vc_exe_name: str) -> Application:
    if not os.path.exists(game_path):
        raise ValueError(f"{game_path=} not found")
    full_exec_path = os.path.join(game_path, vc_exe_name)
    if not os.path.exists(full_exec_path):
        raise ValueError(f"{full_exec_path=} not found")
    full_hdb_path = os.path.join(game_path, "XFiles.hdb")
    if not os.path.exists(full_hdb_path):
        raise ValueError(f"{full_hdb_path=} not found")

    command = f'"{full_exec_path}" "{full_hdb_path}"'
    app = (
        Application()
        .start(
            cmd_line=command,
        )
        .connect(path=full_exec_path)
    )
    app_uia = app #Application(backend='uia').connect(process=app.process)

    dlg: WindowSpecification = app.top_window()
    if dlg.Ignore.exists():
        dlg.Ignore.click()
    return app, app_uia


def main():
    config = parse_config_from_args()
    app, app_uia = start_app(config.game_path, config.vc_exe_name)
    if config.just_open:
        logger.info("App started.")
        exit(0)
    cache = Cache(
        variables=FileCache.load(Variable),
        triggers=FileCache.load(Trigger),
        trigger_actions=FileCache.load(TriggerAction),
        assets=FileCache.load(Asset),
        asset_names=FileCache.load(AssetName),
        view_navigation=FileCache.load(ViewNavigation),
    )
    app["VC Authoring Tool -"].menu_select(r"View -> Screen View")
    app["VC Authoring Tool -"].menu_select(r"View -> Preview")
    app["VC Authoring Tool -"].menu_select(r"View -> Interface List")
    app["VC Authoring Tool -"].menu_select(r"View -> Asset List")
    match config.what_parse:
        case WhatParse.NODES:
            tw = app["VC Authoring Tool -"]["TreeView"]
            el: _treeview_element = tw.tree_root()
            open_all_nodes(el)
            el.select()
            el.click()
            n = None
            try:
                n = parse_nodes(app, app_uia, el, is_first=True, cache=cache)

                n.print_tree()
                with open(config.output_file_name, "w") as f:
                    json.dump(n.model_dump(), f)

                if config.debug:
                    input("Press enter to quit...")
            except KeyboardInterrupt:
                if config.debug:
                    input("Press Ctrl+C again or enter to quit...")
            except Exception:
                logger.exception("Error")
                if config.debug:
                    input("Press enter to quit...")
                app.kill()
                main()
            finally:
                app.kill()
        case WhatParse.ASSETS:
            app["VC Authoring Tool -"].menu_select(r"View -> Asset List")
            try:
                assets = parse_assets(app, cache)
                with open("assets.json", "w") as f:
                    json.dump([x.model_dump() for x in assets], f)
            except KeyboardInterrupt:
                if config.debug:
                    input("Press Ctrl+C again or enter to quit...")
            except Exception:
                logger.exception("Error")
                if config.debug:
                    input("Press enter to quit...")
                app.kill()
                main()
            finally:
                app.kill()


if __name__ == "__main__":
    main()
