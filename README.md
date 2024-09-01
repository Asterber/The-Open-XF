# The Open XF
The Open XF (TOXF for short) is a project aimed at bringing [The X-Files Game](https://en.wikipedia.org/wiki/The_X-Files_Game) to modern platforms with a range of improvements.

**Important!** This project does not distribute any copyrighted files. To use the project, you must install the game from your legal copy!

## Technical Details
- The game was originally developed using the [VirtualCinema©](https://www.virtualcinema.com/) game engine, version `4.0`.
- The engine uses its own `.hdb` format to store game information, such as:
  - Scene tree, variables, and triggers for each scene
  - A list of all assets used (excluding the actual assets)
  - The editor for this engine and its documentation (taken from the official website) is available via the link
  - Video and audio are stored in open formats (QuickTime is required for viewing)
  - All other graphics are stored in proprietary `.pff` files.

## Roadmap
- [ ] Gather the scene tree and all necessary meta-information. Currently, this is partially implemented in the `vc_parser` package. It only works on Windows because it uses [pywinauto](https://github.com/pywinauto/pywinauto) to automate the process of gathering the required information directly from the engine's GUI.
- [ ] Develop a program that can extract static graphics from `.pff` files
- [ ] Develop a custom engine that can work with the output from `vc_parser`.
- [ ] Fix bugs and refine the engine to the point where the game can be completed 100%.
  
  The next phase will involve implementing enhancements:
- [ ] Use AI to improve the quality of video and graphics.
- [ ] Add support for subtitles (absent in the original game).
- [ ] And more...


## Packages
### vc_parser
Parser runs VirtualCinema GUI application and parse meta-information into output file. It supports cache (because parsing process very slow, around 1.5h without caching). Also VirtualCinema crashes sometimes after you click so many times to `trigger actions`
Actual output file always placed in `data` directory of repo.
#### Usage
```powershell
# make sure you set PYTHONPATH variable (windows feature?)
> set PYTHONPATH=%PYTHONPATH%;%cd%
> python parser\main.py
```


## References
- [agrippa](https://github.com/xesf/agrippa) - An excellent project that greatly inspired me. *WIP*
- [The X-Files Game (Wikipedia)](https://en.wikipedia.org/wiki/The_X-Files_Game)
- [VirtualCinema©](https://www.virtualcinema.com/) - The engine on which the original game was built.
