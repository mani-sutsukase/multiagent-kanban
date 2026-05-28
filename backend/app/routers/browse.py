import os
import platform

from fastapi import APIRouter

router = APIRouter(prefix="/api")


@router.get("/browse-directory")
async def browse_directory(path: str = ""):
    """列出指定路径下的子目录。path 为空时返回根目录/驱动器列表。"""
    if not path:
        return _list_roots()
    try:
        entries = []
        with os.scandir(path) as it:
            for entry in it:
                if entry.is_dir():
                    try:
                        full = os.path.join(path, entry.name)
                        entries.append({
                            "name": entry.name,
                            "path": full,
                        })
                    except (OSError, PermissionError):
                        pass
        entries.sort(key=lambda e: e["name"].lower())
        parent = os.path.dirname(os.path.abspath(path))
        return {
            "current": os.path.abspath(path),
            "parent": parent if parent != path else None,
            "entries": entries,
        }
    except (FileNotFoundError, NotADirectoryError, PermissionError, OSError) as e:
        return {"current": path, "parent": None, "entries": [], "error": str(e)}


def _list_roots():
    if platform.system() == "Windows":
        entries = []
        import string
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                entries.append({"name": drive, "path": drive})
        return {"current": "", "parent": None, "entries": entries}
    else:
        entries = [{"name": "/", "path": "/"}]
        return {"current": "", "parent": None, "entries": entries}
