from pywinauto import win32defines
from pywinauto.controls.common_controls import TreeViewWrapper, _treeview_element


def children(tree, force_get_childrens=False):
    """Return the direct children of this control"""
    if tree.item().cChildren not in (0, 1):
        print("##### not dealing with that TVN_GETDISPINFO stuff yet")

    children_elements = []
    if tree.item().cChildren == 1 or force_get_childrens:
        # Get the first child of this element
        child_elem = tree.tree_ctrl.send_message(
            win32defines.TVM_GETNEXTITEM, win32defines.TVGN_CHILD, tree.elem
        )

        if child_elem:
            children_elements.append(_treeview_element(child_elem, tree.tree_ctrl))

            # now get all the next children
            while True:
                next_child = children_elements[-1].next_item()

                if next_child is not None:
                    children_elements.append(next_child)
                else:
                    break
        else:
            return []

    return children_elements


def sub_elements(tree, force_get_childrens: bool):
    """
    Return the list of children of this control

    Rewrite from source code of pywinauto to enforce
    get childrens on items which not got `cChlirden`
    flag set to 1

    Maybe target application error on bug? Idk
    """
    sub_elems = []

    for child in children(tree, force_get_childrens):
        sub_elems.append(child)

        sub_elems.extend(child.sub_elements())

    return sub_elems


def get_selected_item(tree: TreeViewWrapper) -> _treeview_element:
    res = []
    for el in tree.roots():
        el: _treeview_element = el
        res += sub_elements(el, True)
    for r in res:
        if r.is_selected():
            return r
    raise Exception("Can't find selected item in tree view")
