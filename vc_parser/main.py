import argparse
import json
import logging
import os

from pydantic import BaseModel
from pywinauto import WindowSpecification
from pywinauto.application import Application
from pywinauto.controls.common_controls import _treeview_element

from vc_parser.cache import Cache, FileCache
from vc_parser.parsing import open_all_nodes, parse_nodes
from vc_parser.schemas import Trigger, TriggerAction, Variable

logger = logging.getLogger('parser')


class Config(BaseModel):
    game_path: str
    output_file_name: str
    vc_exe_name: str
    debug: bool
    just_open: bool

def parse_config_from_args() -> Config:
    parser = argparse.ArgumentParser(
            description="Program parse .hdb file of The X-Files game into needed structures"
            )
    parser.add_argument("-d", type=str, help="Path with installed game")
    parser.add_argument("-o", type=str, help="Output file name", default="tree.json")
    parser.add_argument("-e", type=str, help="VC executable name which locate in path with installed game", default="vc author 4.0.exe")
    parser.add_argument("--debug", type=bool, help="Enable debug: don't close application window until press enter", default=False)
    parser.add_argument("-jo", type=bool, help="Just open application and exit program", default=False)
    args = vars(parser.parse_args())
    return Config(
            game_path=args['d'],
            output_file_name=args['o'],
            vc_exe_name=args['e'],
            debug=args['debug'],
            just_open=args['jo'],
            )

def start_app(game_path: str, vc_exe_name: str) -> Application:
    if not os.path.exists(game_path):
        raise ValueError(f"{game_path=} not found")
    full_exec_path = os.path.join(game_path, vc_exe_name)
    if not os.path.exists(full_exec_path):
        raise ValueError(f"{full_exec_path=} not found")
    full_hdb_path = os.path.join(game_path, 'XFiles.hdb')
    if not os.path.exists(full_hdb_path):
        raise ValueError(f"{full_hdb_path=} not found")

    command = f'"{full_exec_path}" "{full_hdb_path}"'
    app = Application().start(
            cmd_line=command, 
            ).connect(path=full_exec_path)
    input()

    dlg: WindowSpecification = app.top_window()
    dlg.Ignore.click()
    return app


def main():
    config = parse_config_from_args()
    app = start_app(config.game_path, config.vc_exe_name)
    if config.just_open:
        logger.info("App started.")
        exit(0)
    cache = Cache(
        variables = FileCache.load(Variable),
        triggers = FileCache.load(Trigger),
        trigger_actions = FileCache.load(TriggerAction),
    )
    app['VC Authoring Tool -'].menu_select(r'View -> Screen View')
    tw = app['VC Authoring Tool -']['TreeView']
    el: _treeview_element = tw.tree_root()
    open_all_nodes(el)
    el.select()
    el.click()
    n = None
    try:
        n = parse_nodes(app, el, is_first=True, cache=cache)
        
        n.print_tree()
        with open(config.output_file_name, 'w') as f:
            json.dump(n.model_dump(), f)

        if config.debug:
            input('Press enter to quit...')
    except KeyboardInterrupt:
        if config.debug:
            input("Press Ctrl+C again or enter to quit...")
    except Exception:
        logger.exception("Error")
        if config.debug:
            input('Press enter to quit...')
    finally:
        app.kill()


if __name__ == '__main__':
    main()
