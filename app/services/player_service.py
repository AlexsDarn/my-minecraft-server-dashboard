"""Visor de inventario público: lee world/playerdata/<uuid>.dat (NBT 1.20.x).

Solo muestra jugadores CONECTADOS (se resuelven por el sample de mcstatus),
así no se filtra info de nadie offline y no hay path traversal posible.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

from app import config
from app.services import status_service

# Iconos renderizados por versión (1.20.2 vale para 1.20.1: mismos items).
# Si un icono no existe (bloques van en blocks/, mods no tienen), el slot
# muestra la abreviatura en texto (ver player_modal.html).
ICON_VERSION = getattr(config, "MC_ASSETS_VERSION", "1.20.2")
ICON_BASE = (
    "https://cdn.jsdelivr.net/gh/PrismarineJS/minecraft-assets@master"
    f"/data/{ICON_VERSION}"
)

ENCHANT_NAMES = {
    "protection": "Protection", "fire_protection": "Fire Protection",
    "feather_falling": "Feather Falling", "blast_protection": "Blast Protection",
    "projectile_protection": "Projectile Protection", "respiration": "Respiration",
    "aqua_affinity": "Aqua Affinity", "thorns": "Thorns",
    "depth_strider": "Depth Strider", "frost_walker": "Frost Walker",
    "soul_speed": "Soul Speed", "swift_sneak": "Swift Sneak",
    "sharpness": "Sharpness", "smite": "Smite",
    "bane_of_arthropods": "Bane of Arthropods", "knockback": "Knockback",
    "fire_aspect": "Fire Aspect", "looting": "Looting",
    "sweeping": "Sweeping Edge", "efficiency": "Efficiency",
    "silk_touch": "Silk Touch", "unbreaking": "Unbreaking",
    "fortune": "Fortune", "power": "Power", "punch": "Punch",
    "flame": "Flame", "infinity": "Infinity",
    "luck_of_the_sea": "Luck of the Sea", "lure": "Lure",
    "loyalty": "Loyalty", "impaling": "Impaling", "riptide": "Riptide",
    "channeling": "Channeling", "multishot": "Multishot",
    "quick_charge": "Quick Charge", "piercing": "Piercing",
    "mending": "Mending", "vanishing_curse": "Curse of Vanishing",
    "binding_curse": "Curse of Binding",
}

ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]

DIMENSIONS = {
    "minecraft:overworld": "Overworld",
    "minecraft:the_nether": "Nether",
    "minecraft:the_end": "End",
}


def _roman(lvl: int) -> str:
    return ROMAN[lvl - 1] if 1 <= lvl <= 10 else str(lvl)


def pretty_id(item_id: str) -> str:
    """minecraft:diamond_sword -> Diamond Sword."""
    parts = item_id.split(":", 1)
    name = parts[-1]
    return name.replace("_", " ").title()


def _display_name(tag: dict, item_id: str) -> str:
    """Nombre custom (display.Name es un componente JSON) o el del item."""
    try:
        display = (tag or {}).get("display") or {}
        raw = display.get("Name")
        if raw:
            comp = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(comp, dict):
                if comp.get("text"):
                    extra = "".join(
                        e.get("text", "") for e in comp.get("extra", [])
                        if isinstance(e, dict)
                    )
                    return (comp["text"] + extra).strip() or pretty_id(item_id)
                if comp.get("translate"):
                    return pretty_id(item_id)
    except Exception:
        pass
    return pretty_id(item_id)


def parse_item(entry: dict) -> dict:
    """Un elemento de Inventory/EnderItems a dict serializable."""
    item_id = str(entry.get("id", "minecraft:stone"))
    tag = entry.get("tag") or {}
    enchants = []
    try:
        for e in tag.get("Enchantments", []) or []:
            eid = str(e.get("id", "")).split(":", 1)[-1]
            lvl = int(e.get("lvl", 1))
            enchants.append(f"{ENCHANT_NAMES.get(eid, eid)} {_roman(lvl)}")
    except Exception:
        pass
    short = item_id.split(":", 1)[-1]
    abbr = "".join(w[0] for w in short.split("_")[:2]).upper() or "?"
    return {
        "id": item_id,
        "short": short,
        "abbr": abbr,
        "count": int(entry.get("Count", 1)),
        "name": _display_name(tag, item_id),
        "enchants": enchants,
        "icon": f"{ICON_BASE}/items/{short}.png",
        "icon_fallback": f"{ICON_BASE}/blocks/{short}.png",
    }


def _icons(value: float, maximum: float) -> list[str]:
    """10 iconos full/half/empty escalados al máximo (vida 20, comida 20)."""
    units = max(0, min(round(value / maximum * 20), 20)) if maximum > 0 else 0
    full, half = units // 2, units % 2
    return ["full"] * full + (["half"] if half else []) + ["empty"] * (10 - full - half)


def normalize_uuid(raw: str) -> str:
    h = re.sub(r"[^0-9a-fA-F]", "", raw or "").lower()
    if len(h) != 32:
        raise ValueError("UUID inválido")
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


def playerdata_path(uuid_dashed: str) -> Path:
    # MC_DATA_DIR es la carpeta del mundo (contiene playerdata/).
    return Path(config.MC_DATA_DIR) / "playerdata" / f"{uuid_dashed}.dat"


def parse_playerdata(root: dict) -> dict:
    """Raíz NBT (ya cargada) a dict para el template."""
    inv = root.get("Inventory") or []
    slots: dict[int, dict] = {}
    for entry in inv:
        try:
            slots[int(entry.get("Slot", -999))] = parse_item(dict(entry))
        except Exception:
            continue
    ender = []
    for entry in root.get("EnderItems") or []:
        try:
            ender.append(parse_item(dict(entry)))
        except Exception:
            continue

    max_health = 20.0
    try:
        for attr in root.get("Attributes") or []:
            if str(attr.get("Name")) == "minecraft:generic.max_health":
                max_health = float(attr.get("Base", 20.0))
    except Exception:
        pass
    health = float(root.get("Health", 20.0))
    food = int(root.get("foodLevel", 20))

    try:
        pos = [round(float(x), 1) for x in root.get("Pos", [0, 0, 0])]
    except Exception:
        pos = [0, 0, 0]
    dim = str(root.get("Dimension", "minecraft:overworld"))

    return {
        "health": round(health, 1),
        "max_health": round(max_health, 1),
        "hearts": _icons(health, max_health),
        "food": food,
        "hunger": _icons(food, 20),
        "saturation": round(float(root.get("foodSaturationLevel", 5.0)), 1),
        "xp_level": int(root.get("XpLevel", 0)),
        "pos": pos,
        "dimension": DIMENSIONS.get(dim, dim),
        "selected": int(root.get("SelectedItemSlot", 0)),
        "storage": [slots.get(s) for s in range(9, 36)],
        "hotbar": [slots.get(s) for s in range(0, 9)],
        "armor": {
            "head": slots.get(103),
            "chest": slots.get(102),
            "legs": slots.get(101),
            "feet": slots.get(100),
            "offhand": slots.get(-106),
        },
        "ender": ender,
    }


def get_player(name: str) -> dict:
    """Ficha pública de un jugador CONECTADO. Nunca lanza excepción."""
    mc = status_service.query_status()
    if not mc.get("online"):
        return {"ok": False, "error": "servidor fuera de línea"}
    entry = next(
        (p for p in mc.get("players", []) if p["name"].lower() == name.lower()),
        None,
    )
    if entry is None:
        return {"ok": False, "error": f"{name} no está conectado ahora mismo"}
    try:
        uuid = normalize_uuid(entry["id"])
    except ValueError:
        return {"ok": False, "error": "UUID inválido en el sample"}
    path = playerdata_path(uuid)
    if not path.is_file():
        return {
            "ok": False,
            "error": "aún sin datos de este jugador (entra al mundo primero)",
        }
    try:
        import nbtlib

        root = nbtlib.load(str(path))[""]
        data = parse_playerdata(root)
        mtime = dt.datetime.fromtimestamp(path.stat().st_mtime)
        data.update(
            {
                "ok": True,
                "name": entry["name"],
                "uuid": uuid,
                "updated": mtime.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        return data
    except Exception as e:
        return {"ok": False, "error": f"no se pudo leer su ficha: {e}"}
