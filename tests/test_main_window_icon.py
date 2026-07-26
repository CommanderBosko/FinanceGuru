"""_icon_fallback_path() must resolve correctly both in dev/Nix/Flatpak runs
and inside a PyInstaller-frozen build (sys._MEIPASS set), since a source-tree
relative path computation is meaningless once PyInstaller relocates
everything. See main_window.py for the two branches this test covers.
"""

from financeguru.views.main_window import _icon_fallback_path


def test_uses_source_tree_svg_when_not_frozen(monkeypatch):
    monkeypatch.delattr("sys._MEIPASS", raising=False)
    path = _icon_fallback_path()
    assert path.parts[-6:] == ("share", "icons", "hicolor", "scalable", "apps", "financeguru.svg")


def test_uses_bundled_png_when_frozen(monkeypatch, tmp_path):
    fake_meipass = tmp_path / "bundle"
    fake_meipass.mkdir()
    (fake_meipass / "financeguru.png").touch()
    monkeypatch.setattr("sys._MEIPASS", str(fake_meipass), raising=False)

    path = _icon_fallback_path()

    assert path == fake_meipass / "financeguru.png"
