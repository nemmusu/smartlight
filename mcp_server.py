"""Smartlight MCP server. Run with ``python mcp_server.py`` (stdio).

The desktop service owns all light state. This process only exposes typed MCP
tools and forwards discrete operations over an authenticated loopback channel.
"""

from __future__ import annotations

import argparse
import hmac
import os
import sys
from typing import Annotated, Any, Literal

# The console executable is also the isolated host for the optional vendor SDK.
if __name__ == "__main__" and "--mystic-worker" in sys.argv:
    from mystic_light import worker_main
    raise SystemExit(worker_main(sys.argv[sys.argv.index("--mystic-worker") + 1]))

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

if __package__:
    from .bridge_client import BridgeError, invoke_async
else:
    from bridge_client import BridgeError, invoke_async


mcp = MCPServer("Smartlight")
READ = ToolAnnotations(read_only_hint=True, open_world_hint=False)
WRITE = ToolAnnotations(destructive_hint=False, idempotent_hint=True, open_world_hint=False)
ACTION = ToolAnnotations(destructive_hint=False, idempotent_hint=False, open_world_hint=False)
DELETE = ToolAnnotations(destructive_hint=True, idempotent_hint=True, open_world_hint=False)

Brightness = Annotated[int, Field(ge=1, le=100, description="Luminosità da 1 a 100")]
HexColor = Annotated[str, Field(pattern=r"^#[0-9a-fA-F]{6}$", description="Colore HEX, ad esempio #FF8800")]
Hue = Annotated[int, Field(ge=0, le=360, description="Tonalità HSV in gradi")]
Saturation = Annotated[int, Field(ge=0, le=100, description="Saturazione da 0 a 100")]
Kelvin = Annotated[int, Field(ge=2500, le=9000, description="Temperatura colore in kelvin; intervallo effettivo secondo dispositivo")]
Target = Annotated[str | list[str], Field(description="'all', 'room:<id>', ID/key di list_targets, oppure lista di ID/key; es. ['striscia', 'openrgb:Logitech G512 RGB']")]
AnimationDefinition = Annotated[dict[str, Any], Field(
    description="Es. {'colors':['#0088FF'],'mode':'breathe','step_ms':2000,'brightness':100,'min_brightness':0,'speed':50,'include_pc':true}; preferisci save_custom_effect")]
ScheduleDefinition = Annotated[dict[str, Any], Field(
    description="Es. {'time':'22:30','target':'all','days':[1,2,3,4,5,6,7],'enabled':true,'action':{'power':true,'color':'#00FF00','brightness':30}}. Per una sola data: days=[] e once_date='2026-10-15' (AAAA-MM-GG, data locale futura). Preferisci save_lighting_schedule")]
SceneStates = Annotated[dict[str, Any], Field(
    description="Ometti per catturare lo stato corrente; altrimenti {'tapo': {ID: {'power':true,'hue':240,'saturation':100,'brightness':50}}, 'pc': {'devices': {KEY: {'on':true,'effect':'statico','color':[0,0,255],'brightness':50}}}}")]
PCState = Annotated[dict[str, Any], Field(
    description="Campi facoltativi: on bool, effect ID da list_pc_effects, color/color2 [R,G,B] (0..255), speed 0.2..4.0, brightness 0..100. Es. {'on':true,'effect':'statico','color':[0,255,0],'brightness':80}")]
SyncConfig = Annotated[dict[str, Any], Field(
    description="Es. {'mode':'pc_to_tapo','source':'auto','target':'all','interval_ms':1000}; mode può essere 'off' o 'pc_to_tapo', intervallo 1000..60000 ms")]


async def _call(command: str, **params: Any) -> dict[str, Any]:
    try:
        return await invoke_async(command, {key: value for key, value in params.items() if value is not None})
    except BridgeError as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool(annotations=READ)
async def list_devices() -> dict[str, Any]:
    """Elenca Tapo e RGB PC con ID e nomi reali, senza inventare periferiche.

    Ogni dispositivo PC include kind (es. KEYBOARD, MOUSE, FAN) e category:
    usa questi campi per riconoscere tastiera, mouse e altre parti del PC.
    Per i gruppi creati dall'utente chiama list_rooms.
    """
    return await _call("devices.list")


@mcp.tool(annotations=READ)
async def list_rooms() -> dict[str, Any]:
    """Elenca le stanze Smartlight con Tapo device_ids e RGB PC pc_keys.

    Sono gruppi creati in Smartlight, indipendenti dalle stanze dell'app Tapo.
    Per agire su una stanza usa target='room:<id>' nei tool per Tapo+PC.
    """
    return await _call("rooms.list")


@mcp.tool(annotations=WRITE)
async def save_room(name: str, device_ids: list[str], pc_keys: list[str] | None = None, id: str | None = None) -> dict[str, Any]:
    """Crea o modifica un gruppo Tapo/PC; usa gli ID esatti di list_targets.

    Esempio: name='Scrivania', device_ids=['striscia'],
    pc_keys=['openrgb:Logitech G512 RGB']. Per modificarlo passa anche l'id
    restituito da list_rooms. Poi usa 'room:<id>' come target degli altri tool.
    """
    return await _call("rooms.save", name=name, device_ids=device_ids, pc_keys=pc_keys or [], id=id)


@mcp.tool(annotations=DELETE)
async def delete_room(id: str) -> dict[str, Any]:
    """Elimina una stanza salvata, lasciando disponibili i suoi dispositivi."""
    return await _call("rooms.delete", id=id)


@mcp.tool(annotations=READ)
async def list_targets() -> dict[str, Any]:
    """Elenca i target per i comandi misti Tapo/PC e i relativi ID.

    Usa 'all' per tutte le luci, 'room:<id>' per una stanza salvata, oppure
    un ID/key esatto. La risposta include nomi, kind e category dei dispositivi
    PC (KEYBOARD indica una tastiera) e i membri Tapo/PC di ogni stanza.
    Leggi questa lista prima di comporre una selezione.
    """
    return await _call("targets.list")


@mcp.tool(annotations=READ)
async def get_lighting_overview() -> dict[str, Any]:
    """Leggi in forma compatta tutti i dispositivi Tapo/PC, stati, effetti e scene.

    Primo passo per richieste sulle luci: leggi ID/key e capacità reali, scegli
    il tool adatto, poi verifica l'esito con questo tool o get_device_status.
    Non inventare ID o nomi di effetti. Per 'tutte verdi' usa set_color con
    target='all' e color='#00FF00'. Per gruppi usa list_rooms/save_room e
    target='room:<id>'. Per effetti personalizzati usa save_custom_effect,
    poi start_animation. Non include i singoli frame LED della tastiera.
    """
    return await _call("lighting.overview")


@mcp.tool(annotations=WRITE)
async def apply_target_state(target: Target, color: str | None = None,
                             brightness: Brightness | None = None, power: bool | None = None,
                             hue: Hue | None = None, saturation: Saturation | None = None) -> dict[str, Any]:
    """Modifica insieme luci Tapo e RGB PC; specifica solo i campi da cambiare.

    Esempio: target='all', color='#00FF00', brightness=60, power=True.
    target accetta 'all', 'room:<id>', un ID/key o una lista da list_targets.
    color usa #RRGGBB; hue e saturation sono una coppia HSV alternativa.
    Per il bianco in kelvin usa set_color_temperature sulle sole Tapo.
    """
    return await _call("target.apply", target=target, color=color, brightness=brightness,
                       power=power, hue=hue, saturation=saturation)


@mcp.tool(annotations=WRITE)
async def set_color(target: Target, color: HexColor,
                    brightness: Brightness | None = None) -> dict[str, Any]:
    """Scegli un colore HEX e accendi tutte le luci selezionate, Tapo e PC.

    Esempio: target='all', color='#00FF00', brightness=70 mette tutte le luci
    verdi al 70%. target accetta 'all', 'room:<id>', un ID/key o una lista
    degli ID/key restituiti da list_targets.
    """
    return await _call("target.apply", target=target, color=color, brightness=brightness, power=True)


@mcp.tool(annotations=WRITE)
async def set_lights_power(target: Target, on: bool) -> dict[str, Any]:
    """Accendi o spegni Tapo e RGB PC per tutti, una stanza o una selezione.

    Esempio: target='room:scrivania', on=False. Usa list_targets per gli ID.
    """
    return await _call("target.apply", target=target, power=on)


@mcp.tool(annotations=WRITE)
async def set_lights_brightness(target: Target, brightness: Brightness) -> dict[str, Any]:
    """Regola la luminosità Tapo e PC (1-100) senza cambiare il colore.

    Esempio: target='all', brightness=40. Per spegnere usa set_lights_power.
    """
    return await _call("target.apply", target=target, brightness=brightness)


@mcp.tool(annotations=READ)
async def get_control_mode() -> dict[str, Any]:
    """Mostra chi controlla ora le luci: animazione, sincronizzazione o colore statico."""
    return await _call("modes.status")


@mcp.tool(annotations=READ)
async def get_device_status(device: str) -> dict[str, Any]:
    """Leggi stato, colore, luminosità ed effetto corrente di una luce."""
    return await _call("devices.status", device=device)


@mcp.tool(annotations=READ)
async def get_device_capabilities(device: str) -> dict[str, Any]:
    """Leggi funzioni e limiti realmente disponibili per una luce."""
    return await _call("devices.capabilities", device=device)


@mcp.tool(annotations=ACTION)
async def rescan_devices() -> dict[str, Any]:
    """Cerca nuovamente le luci Tapo nella rete locale."""
    return await _call("devices.rescan")


@mcp.tool(annotations=WRITE)
async def set_power(device: str, on: bool) -> dict[str, Any]:
    """Accendi o spegni una luce Tapo."""
    return await _call("lights.set", device=device, power=on)


@mcp.tool(annotations=WRITE)
async def set_brightness(device: str, brightness: Brightness) -> dict[str, Any]:
    """Imposta la luminosità di una luce Tapo."""
    return await _call("lights.set", device=device, brightness=brightness)


@mcp.tool(annotations=WRITE)
async def set_color_hsv(device: str, hue: Hue, saturation: Saturation, brightness: Brightness | None = None) -> dict[str, Any]:
    """Imposta HSV su una luce Tapo. Per Tapo e PC insieme usa set_color."""
    return await _call("lights.set", device=device, hue=hue, saturation=saturation, brightness=brightness)


@mcp.tool(annotations=WRITE)
async def set_color_temperature(device: str, kelvin: Kelvin, brightness: Brightness | None = None) -> dict[str, Any]:
    """Imposta il bianco in kelvin su una luce Tapo; il PC RGB non offre questa modalità."""
    return await _call("lights.set", device=device, kelvin=kelvin, brightness=brightness)


@mcp.tool(annotations=WRITE)
async def apply_tapo_device_preset(device: str, preset: str) -> dict[str, Any]:
    """Applica uno slot preset nativo Tapo elencato da get_device_status."""
    return await _call("lights.set", device=device, device_preset=preset)


@mcp.tool(annotations=READ)
async def list_effects(device: str) -> dict[str, Any]:
    """Elenca effetti nativi e personalizzati disponibili per una luce."""
    return await _call("effects.list", device=device)


@mcp.tool(annotations=WRITE)
async def apply_effect(device: str, effect: str, brightness: Brightness | None = None) -> dict[str, Any]:
    """Attiva un effetto della luce, con luminosità facoltativa."""
    return await _call("effects.apply", device=device, effect=effect, brightness=brightness)


@mcp.tool(annotations=WRITE)
async def save_custom_effect(
    name: str,
    colors: Annotated[list[str], Field(min_length=1, max_length=20, description="Da 1 a 20 colori HEX, es. #FF8800")],
    mode: Literal["flow", "cycle", "pulse", "random", "wave", "static", "sequence", "breathe", "gradient", "rainbow", "flash"] = "cycle",
    step_ms: Annotated[int, Field(ge=500, le=60000)] = 1000,
    brightness: Brightness = 100,
    min_brightness: Annotated[int, Field(ge=0, le=100, description="Minimo della pulsazione/respiro, <= brightness. 0 = minimo disponibile: 0% su RGB PC, su alcune Tapo può essere 1%")] = 0,
    loop: bool = True,
    speed: Annotated[int, Field(ge=1, le=100)] = 50,
    direction: Literal["forward", "reverse", "alternate"] = "forward",
    transition_ms: Annotated[int, Field(ge=0, le=10000)] = 500,
    include_pc: bool = False,
    id: str | None = None,
) -> dict[str, Any]:
    """Crea/aggiorna un'animazione Tapo e, con include_pc, anche PC.

    Esempio completo: name='Respiro blu', colors=['#0088FF'], mode='breathe',
    step_ms=2000, brightness=100, min_brightness=0, speed=50,
    include_pc=True. Salva l'effetto, poi usa start_animation con il nome.
    pulse e breathe sfumano tra brightness (massimo) e min_brightness
    (minimo disponibile: 0% su PC, alcune Tapo arrivano a 1%); flow, gradient, wave e rainbow
    muovono i colori in modo continuo. sequence e cycle mantengono un colore
    per step_ms e sfumano verso il successivo negli ultimi transition_ms;
    transition_ms=0 rende il cambio immediato. flash e random hanno cambi
    volutamente netti. speed=50 usa i tempi indicati; un valore più alto
    accelera l'effetto. Il ciclo di pulse/breathe dura circa
    max(2 secondi, step_ms * max(2, numero_colori) * 50 / speed * 3 / 1000),
    fino a 600 secondi. loop=False esegue un solo ciclo.
    """
    if min_brightness > brightness:
        raise ValueError("min_brightness deve essere <= brightness")
    definition = {"colors": colors, "mode": mode, "step_ms": step_ms, "brightness": brightness,
                  "min_brightness": min_brightness,
                  "loop": loop, "speed": speed, "direction": direction,
                  "transition_ms": transition_ms, "include_pc": include_pc}
    return await _call("animations.save", name=name, definition=definition, id=id)


@mcp.tool(annotations=DELETE)
async def delete_custom_effect(name: str) -> dict[str, Any]:
    """Elimina un effetto animato personalizzato gestito da Smartlight."""
    return await _call("animations.delete", name=name)


@mcp.tool(annotations=READ)
async def list_presets(device: str | None = None) -> dict[str, Any]:
    """Elenca preset luce, inclusi quelli salvati in Smartlight."""
    return await _call("presets.list", device=device)


@mcp.tool(annotations=WRITE)
async def save_preset(
    name: str,
    state: Annotated[dict[str, Any], Field(description="Colore: {'color':'#00FF00','brightness':60}; animazione: {'kind':'animation','animation_id':'<id>'}; tema: {'kind':'theme','theme_id':'<id>'}; effetto Tapo: {'kind':'native_effect','effect':'Relax'}; effetto PC: {'kind':'pc_effect','effect':'onda','color':'#0088FF','color2':'#FF8800','speed':1.0,'brightness':80}. Gli ID degli effetti PC vengono da list_pc_effects")],
    device: str | None = None,
) -> dict[str, Any]:
    """Salva un preset riutilizzabile; per casi comuni usa i tool save_*_preset.

    Esempio colore: name='Verde', state={'color':'#00FF00',
    'brightness':60}. Esempio animazione: state={'kind':'animation',
    'animation_id':'<id da list_animations>'}. Supporta anche gli effetti Tapo
    e PC; per quelli usa save_tapo_effect_preset o save_pc_effect_preset.
    Poi usa apply_preset.
    """
    return await _call("presets.save", name=name, state=state, device=device)


@mcp.tool(annotations=WRITE)
async def save_color_preset(name: str, color: HexColor, brightness: Brightness = 100,
                            target: str = "all", id: str | None = None) -> dict[str, Any]:
    """Salva o aggiorna un preset colore riutilizzabile su Tapo e RGB PC."""
    return await _call("presets.save", name=name, state={"color": color, "brightness": brightness},
                       device=target, id=id)


@mcp.tool(annotations=WRITE)
async def save_animation_preset(name: str, animation_id: str) -> dict[str, Any]:
    """Salva un preset che avvia un'animazione Smartlight esistente."""
    return await _call("presets.save", name=name, state={"kind": "animation", "animation_id": animation_id})


@mcp.tool(annotations=WRITE)
async def save_theme_preset(name: str, theme_id: str) -> dict[str, Any]:
    """Salva un preset che applica un tema Smartlight esistente."""
    return await _call("presets.save", name=name, state={"kind": "theme", "theme_id": theme_id})


@mcp.tool(annotations=WRITE)
async def save_tapo_effect_preset(name: str, effect: str) -> dict[str, Any]:
    """Salva un effetto originale Tapo come preset riutilizzabile.

    Usa il nome esatto elencato in get_device_status (campo effects) di una
    luce, per esempio effect='Relax'. Il preset si applica solo alle Tapo
    compatibili nella destinazione scelta con apply_preset.
    """
    return await _call("presets.save", name=name, state={"kind": "native_effect", "effect": effect})


@mcp.tool(annotations=WRITE)
async def save_pc_effect_preset(name: str, effect: str, color: HexColor = "#64B6FF",
                                color2: HexColor = "#FFB86B",
                                speed: Annotated[float, Field(ge=0.2, le=4.0)] = 1.0,
                                brightness: Annotated[int, Field(ge=0, le=100)] = 100) -> dict[str, Any]:
    """Salva effetto RGB PC, due colori, velocità e luminosità come preset.

    Usa l'ID esatto da list_pc_effects, per esempio effect='onda', e colori
    HEX come '#0088FF'. Applica con apply_preset a una luce PC, stanza o 'all':
    nella destinazione cambiano solo le luci PC.
    """
    return await _call("presets.save", name=name, state={"kind": "pc_effect", "effect": effect,
                "color": color, "color2": color2, "speed": speed, "brightness": brightness})


@mcp.tool(annotations=WRITE)
async def apply_preset(name: str, device: str | None = None) -> dict[str, Any]:
    """Applica un preset Smartlight a 'all', una stanza 'room:<id>' o un ID luce.

    I preset colore, tema e animazione agiscono sui dispositivi supportati;
    un effetto Tapo originale agisce solo sulle Tapo compatibili, uno RGB PC
    solo sulle luci PC. Per conoscere gli ID usa list_targets e list_presets.
    """
    return await _call("presets.apply", name=name, device=device)


@mcp.tool(annotations=DELETE)
async def delete_preset(name: str, device: str | None = None) -> dict[str, Any]:
    """Elimina un preset personalizzato salvato in Smartlight."""
    return await _call("presets.delete", name=name, device=device)


@mcp.tool(annotations=READ)
async def list_scenes() -> dict[str, Any]:
    """Elenca scene che possono coordinare luci Tapo e PC."""
    return await _call("scenes.list")


@mcp.tool(annotations=WRITE)
async def save_scene(name: str, states: SceneStates | None = None,
                     target: str | list[str] | None = None,
                     description: str = "", include_tapo: bool = True,
                     include_pc: bool = True) -> dict[str, Any]:
    """Salva una scena per ripristinare più luci insieme.

    Esempio semplice: passa solo name='Sera' per fotografare lo stato corrente.
    Puoi limitare la cattura con target='room:<id>' o una lista da list_targets.
    Per stati espliciti: states={'tapo': {'striscia': {'power': True,
    'hue': 240, 'saturation': 100, 'brightness': 50}}, 'pc': {'devices':
    {'openrgb:Logitech G512 RGB': {'on': True, 'effect': 'statico',
    'color': [0, 0, 255], 'brightness': 50}}}}. Poi usa apply_scene.
    """
    return await _call("scenes.save", name=name, states=states, target=target,
                       description=description, include_tapo=include_tapo, include_pc=include_pc)


@mcp.tool(annotations=ACTION)
async def apply_scene(name: str) -> dict[str, Any]:
    """Applica una scena salvata a tutti i dispositivi associati."""
    return await _call("scenes.apply", name=name)


@mcp.tool(annotations=DELETE)
async def delete_scene(name: str) -> dict[str, Any]:
    """Elimina una scena salvata."""
    return await _call("scenes.delete", name=name)


@mcp.tool(annotations=READ)
async def list_themes() -> dict[str, Any]:
    """Elenca i temi coordinati già inclusi per luci Tapo e RGB del PC."""
    return await _call("themes.list")


@mcp.tool(annotations=ACTION)
async def apply_theme(id: str, target: str | list[str] | None = None,
                      mode: Literal["static", "animated"] | None = None) -> dict[str, Any]:
    """Applica un tema statico o animato a tutti, una stanza o una selezione.

    Trova l'id con list_themes. Esempio: id='<id da list_themes>',
    target='all', mode='animated'. Ometti target per usare quello del tema.
    """
    return await _call("theme_apply", id=id, target=target, mode=mode)


@mcp.tool(annotations=WRITE)
async def save_theme(name: str, colors: list[str], mode: Literal["static", "animated"] = "static",
                     brightness: Brightness = 100, step_ms: int = 1000,
                     speed: int = 50, id: str | None = None) -> dict[str, Any]:
    """Crea un tema con una palette per Tapo e PC; applicalo con apply_theme.

    Esempio: name='Tramonto', colors=['#FF8800','#FF3366'],
    mode='animated', brightness=60, step_ms=1500, speed=50.
    I colori sono #RRGGBB; usa l'id restituito per modificarlo.
    """
    return await _call("themes.save", name=name, colors=colors, mode=mode,
                       brightness=brightness, step_ms=step_ms, speed=speed, id=id)


@mcp.tool(annotations=DELETE)
async def delete_theme(id: str) -> dict[str, Any]:
    """Elimina un tema personalizzato; i temi inclusi restano disponibili."""
    return await _call("themes.delete", id=id)


@mcp.tool(annotations=READ)
async def list_animations() -> dict[str, Any]:
    """Elenca animazioni luce personalizzate e stato di riproduzione."""
    return await _call("animations.list")


@mcp.tool(annotations=WRITE)
async def save_animation(name: str, definition: AnimationDefinition) -> dict[str, Any]:
    """Crea un'animazione con definizione completa; preferisci save_custom_effect.

    Esempio valido: name='Respiro blu', definition={'colors':['#0088FF'],
    'mode':'breathe', 'step_ms':2000, 'brightness':100, 'min_brightness':0,
    'speed':50, 'loop':True, 'include_pc':True}. Usa 'colors', non 'steps'.
    Mode: flow/cycle/pulse/random/wave/static/sequence/breathe/gradient/
    rainbow/flash. step_ms 500..60000; transition_ms 0..10000;
    speed 1..100; brightness 1..100; min_brightness 0..brightness.
    """
    return await _call("animations.save", name=name, definition=definition)


@mcp.tool(annotations=ACTION)
async def start_animation(name: str, devices: list[str] | None = None,
                          target: str | list[str] | None = None) -> dict[str, Any]:
    """Avvia un'animazione salvata su tutte le luci o una selezione.

    Esempio: name='Respiro blu', target='all'. Oppure target='room:<id>'
    o target=['striscia', 'openrgb:Logitech G512 RGB']. Leggi gli ID con
    list_targets e i nomi delle animazioni con list_animations.
    """
    return await _call("animations.start", name=name, devices=devices, target=target)


@mcp.tool(annotations=WRITE)
async def stop_animation(name: str | None = None) -> dict[str, Any]:
    """Ferma un'animazione per nome o tutte quelle attive."""
    return await _call("animations.stop", name=name)


@mcp.tool(annotations=DELETE)
async def delete_animation(name: str) -> dict[str, Any]:
    """Elimina una definizione di animazione."""
    return await _call("animations.delete", name=name)


@mcp.tool(annotations=READ)
async def list_schedules() -> dict[str, Any]:
    """Elenca le pianificazioni locali di Smartlight."""
    return await _call("schedules.list")


@mcp.tool(annotations=WRITE)
async def save_schedule(name: str, definition: ScheduleDefinition) -> dict[str, Any]:
    """Crea una pianificazione avanzata; per casi comuni usa save_lighting_schedule.

    Esempio: name='Sera', definition={'time':'22:30', 'target':'all',
    'days':[1,2,3,4,5,6,7], 'enabled':True,
    'action':{'power':True,'color':'#00FF00','brightness':30}}.
    Ora locale HH:MM; giorni 1=lunedì..7=domenica; days=[] una sola volta,
    anche in una data specifica con once_date='2026-10-15' (AAAA-MM-GG).
    action accetta power, color, brightness, hue/saturation o temperature.
    Smartlight deve restare avviato per eseguire la pianificazione.
    """
    return await _call("schedules.save", name=name, definition=definition)


@mcp.tool(annotations=WRITE)
async def save_lighting_schedule(
    name: str, time: Annotated[str, Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$", description="Ora locale HH:MM, es. 22:30")], target: Target,
    action: Literal["on", "off", "color"],
    repeat: Literal["once", "daily", "weekdays", "weekend", "custom"] = "daily",
    days: list[Annotated[int, Field(ge=1, le=7)]] | None = None,
    color: HexColor | None = None, brightness: Brightness | None = None,
    enabled: bool = True, id: str | None = None,
    once_date: Annotated[str | None, Field(pattern=r"^\d{4}-\d{2}-\d{2}$", description="Solo con repeat='once': data locale AAAA-MM-GG, es. 2026-10-15. Ometti per la prossima occorrenza dell'ora.")] = None,
) -> dict[str, Any]:
    """Programma Tapo e RGB PC all'ora locale HH:MM.

    Esempio: name='Sera verde', time='22:30', target='all', action='color',
    color='#00FF00', brightness=30, repeat='daily'. Per repeat='custom',
    passa days=[1,3,5] (1=lunedì, 7=domenica). 'once' esegue la prossima
    occorrenza dell'ora, oppure once_date='2026-10-15' per una data precisa.
    Usa list_targets per i dispositivi e list_schedules
    per verificare il risultato. Smartlight deve restare avviato.
    """
    day_sets = {"once": [], "daily": [1, 2, 3, 4, 5, 6, 7],
                "weekdays": [1, 2, 3, 4, 5], "weekend": [6, 7]}
    if repeat == "custom":
        if not days:
            raise ToolError("Per repeat='custom' specifica almeno un giorno da 1 a 7.")
        selected_days = sorted(set(days))
    else:
        if days is not None:
            raise ToolError("Il parametro days è ammesso solo con repeat='custom'.")
        selected_days = day_sets[repeat]
    if once_date is not None and repeat != "once":
        raise ToolError("once_date è ammesso solo con repeat='once'.")
    if action == "color":
        if color is None:
            raise ToolError("Per action='color' specifica un colore HEX.")
        patch = {"power": True, "color": color}
        if brightness is not None:
            patch["brightness"] = brightness
    else:
        if color is not None or brightness is not None:
            raise ToolError("Colore e luminosità richiedono action='color'.")
        patch = {"power": action == "on"}
    definition = {"target": target, "time": time, "days": selected_days,
                  "enabled": enabled, "action": patch}
    if once_date is not None:
        definition["once_date"] = once_date
    if id is not None:
        definition["id"] = id
    return await _call("schedules.save", name=name, definition=definition)


@mcp.tool(annotations=DELETE)
async def delete_schedule(name: str) -> dict[str, Any]:
    """Elimina una pianificazione locale."""
    return await _call("schedules.delete", name=name)


@mcp.tool(annotations=WRITE)
async def toggle_schedule(id: str, enabled: bool) -> dict[str, Any]:
    """Abilita o disabilita una pianificazione usando il suo ID."""
    return await _call("schedule_toggle", id=id, enabled=enabled)


@mcp.tool(annotations=READ)
async def get_energy(device: str, period: Literal["today", "7d", "30d"] = "today") -> dict[str, Any]:
    """Leggi i dati di consumo energetico se il dispositivo Tapo li supporta."""
    return await _call("energy", id=device, period=period)


@mcp.tool(annotations=WRITE)
async def set_timer(device: str, minutes: Annotated[int, Field(ge=1, le=10080)], action: Literal["on", "off"]) -> dict[str, Any]:
    """Accendi o spegni dopo 1..10080 minuti un dispositivo o una stanza.

    Esempio: device='striscia', minutes=30, action='off'. Usa list_targets
    per l'ID; per un orario fisso usa save_lighting_schedule.
    """
    return await _call("timer_set", id=device, minutes=minutes, action=action)


@mcp.tool(annotations=WRITE)
async def set_away_mode(device: str, enabled: bool, from_time: str | None = None, to_time: str | None = None) -> dict[str, Any]:
    """Attiva o disattiva la simulazione di presenza per una luce o tutte."""
    return await _call("away_set", id=device, enabled=enabled, **{"from": from_time, "to": to_time})


@mcp.tool(annotations=READ)
async def get_sync_status() -> dict[str, Any]:
    """Leggi stato e configurazione della sincronizzazione colori PC verso Tapo."""
    return await _call("sync.status")


@mcp.tool(annotations=WRITE)
async def configure_sync(config: SyncConfig) -> dict[str, Any]:
    """Sincronizza i colori del PC verso le luci Tapo.

    Esempio: config={'mode':'pc_to_tapo', 'source':'auto', 'target':'all',
    'interval_ms':1000}. Leggi gli ID con list_targets e lo stato con
    get_sync_status. Per fermare usa stop_sync oppure mode='off'.
    """
    return await _call("sync.configure", config=config)


@mcp.tool(annotations=WRITE)
async def stop_sync() -> dict[str, Any]:
    """Interrompi la sincronizzazione in esecuzione."""
    return await _call("sync.stop")


@mcp.tool(annotations=ACTION)
async def export_backup(path: str | None = None) -> dict[str, Any]:
    """Esporta la configurazione; senza path usa la cartella dati di Smartlight."""
    return await _call("backup.export", path=path)


@mcp.tool(annotations=DELETE)
async def import_backup(path: str) -> dict[str, Any]:
    """Importa un backup locale, sostituendo la configurazione corrispondente."""
    return await _call("backup.import", path=path)


@mcp.tool(annotations=READ)
async def list_pc_devices() -> dict[str, Any]:
    """Elenca RGB PC con key esatta, name, kind e category rilevati.

    Esempio: kind='KEYBOARD' identifica una tastiera; kind='MOUSE' un mouse.
    Usa la key restituita, non il nome visibile, in set_pc_effect e
    set_pc_device. Se kind='UNKNOWN' o generico, verifica il nome e non
    presumere che la periferica sia una tastiera.
    """
    return await _call("pc.devices")


@mcp.tool(annotations=READ)
async def get_pc_status() -> dict[str, Any]:
    """Leggi connessioni OpenRGB/iCUE, stato e periferiche RGB del PC."""
    return await _call("pc.devices")


@mcp.tool(annotations=ACTION)
async def get_pc_errors() -> dict[str, Any]:
    """Leggi e svuota il registro degli errori recenti delle periferiche RGB."""
    return await _call("pc.errors")


@mcp.tool(annotations=READ)
async def list_pc_effects() -> dict[str, Any]:
    """Elenca effetti RGB disponibili per le periferiche del PC."""
    return await _call("pc.effects")


@mcp.tool(annotations=WRITE)
async def set_pc_effect(devices: list[str], effect: str,
                        color: HexColor | None = None, color2: HexColor | None = None,
                        speed: Annotated[float, Field(ge=0.2, le=4.0)] | None = None,
                        brightness: Annotated[int, Field(ge=0, le=100)] | None = None) -> dict[str, Any]:
    """Applica un effetto RGB a una o più periferiche del PC.

    Esempio: devices=['openrgb:Logitech G512 RGB'], effect='respiro',
    color='#0088FF', speed=0.7, brightness=60. Leggi key ed effetti con
    list_pc_devices e list_pc_effects. I colori sono HEX; speed 0.2..4.0.
    Questo comando cambia solo i dispositivi PC.
    """
    state: dict[str, Any] = {"effect": effect, "on": True}
    if color is not None:
        state["color"] = [int(color[index:index + 2], 16) for index in (1, 3, 5)]
    if color2 is not None:
        state["color2"] = [int(color2[index:index + 2], 16) for index in (1, 3, 5)]
    if speed is not None:
        state["speed"] = speed
    if brightness is not None:
        state["brightness"] = brightness
    return await _call("pc.apply_to", devices=devices, state=state)


@mcp.tool(annotations=READ)
async def list_pc_scenes() -> dict[str, Any]:
    """Elenca le scene PC e i comandi rapidi, incluso 'keyboard_only'."""
    return await _call("pc.scenes")


@mcp.tool(annotations=ACTION)
async def apply_pc_scene(id: str) -> dict[str, Any]:
    """Applica una scena PC inclusa; consulta list_pc_scenes per gli ID."""
    return await _call("pc.scene.apply", id=id)


@mcp.tool(annotations=WRITE)
async def set_pc_device(device: str, state: PCState) -> dict[str, Any]:
    """Imposta una periferica RGB PC; preferisci set_pc_effect per effetti comuni.

    Esempio: device='openrgb:Logitech G512 RGB', state={'on':True,
    'effect':'statico', 'color':[0,255,0], 'brightness':80}.
    Colori RGB sono liste [rosso,verde,blu] da 0 a 255, non stringhe HEX.
    Usa list_pc_devices per la key e list_pc_effects per gli ID effetti.
    """
    return await _call("pc.set_device", device=device, state=state)


@mcp.tool(annotations=WRITE)
async def apply_to_pc_devices(devices: list[str], state: PCState) -> dict[str, Any]:
    """Applica lo stesso stato RGB a più periferiche PC.

    Esempio: devices=['openrgb:Logitech G512 RGB'],
    state={'on':True,'effect':'statico','color':[0,255,0],'brightness':80}.
    Per dispositivi Tapo e PC insieme usa apply_target_state.
    """
    return await _call("pc.apply_to", devices=devices, state=state)


@mcp.tool(annotations=WRITE)
async def set_pc_global(state: dict[str, Any]) -> dict[str, Any]:
    """Imposta la luminosità globale PC con state={'brightness': 0..100}."""
    return await _call("pc.set_global", state=state)


@mcp.tool(annotations=WRITE)
async def set_pc_global_brightness(brightness: Annotated[int, Field(ge=0, le=100)]) -> dict[str, Any]:
    """Imposta la luminosità globale del PC (0–100), senza cambiare quella Tapo."""
    return await _call("pc.set_global", state={"brightness": brightness})


@mcp.tool(annotations=READ)
async def list_pc_profiles() -> dict[str, Any]:
    """Elenca i profili RGB del PC."""
    return await _call("pc.profiles.list")


@mcp.tool(annotations=WRITE)
async def save_pc_profile(name: str) -> dict[str, Any]:
    """Salva lo stato RGB del PC come profilo."""
    return await _call("pc.profiles.save", name=name)


@mcp.tool(annotations=ACTION)
async def load_pc_profile(name: str) -> dict[str, Any]:
    """Carica e applica un profilo RGB del PC."""
    return await _call("pc.profiles.load", name=name)


@mcp.tool(annotations=DELETE)
async def delete_pc_profile(name: str) -> dict[str, Any]:
    """Elimina un profilo RGB del PC."""
    return await _call("pc.profiles.delete", name=name)


@mcp.tool(annotations=ACTION)
async def rescan_pc_devices() -> dict[str, Any]:
    """Cerca di nuovo le periferiche RGB del PC."""
    return await _call("pc.rescan")


if os.name == "nt":
    @mcp.tool(annotations=ACTION)
    async def release_icue() -> dict[str, Any]:
        """Rilascia il controllo iCUE delle periferiche Corsair (solo Windows)."""
        return await _call("pc.release_icue")


@mcp.tool(annotations=READ)
async def get_settings() -> dict[str, Any]:
    """Leggi le preferenze Smartlight e se l'account Tapo è configurato; non restituisce credenziali."""
    return await _call("settings_get")


@mcp.tool(annotations=READ)
async def get_pc_setup() -> dict[str, Any]:
    """Read PC lighting setup / Leggi configurazione PC: detected hardware/software, active backend, missing dependencies and official setup links. Read-only; does not install or change lights. Installed software alone does not prove compatible hardware. Start here when no PC devices are found."""
    return await _call("setup.status")


@mcp.tool(annotations=WRITE)
async def set_settings(auto_start: bool | None = None,
                       minimize_to_tray: bool | None = None,
                       restore_scene: bool | None = None,
                       mcp_auto_start: bool | None = None,
                       mcp_scope: Literal["local", "lan"] | None = None,
                       language: Literal["it", "en"] | None = None,
                       pc_backend_mode: Literal["auto", "openrgb", "icue", "mystic"] | None = None,
                       mystic_light_enabled: bool | None = None,
                       mystic_light_dll: str | None = None) -> dict[str, Any]:
    """Update preferences / Aggiorna preferenze. language='it' or 'en' changes UI/help/tray. Omitted fields stay unchanged. pc_backend_mode defaults to 'auto': Windows uses iCUE/OpenRGB, then experimental MSI only if no PC lights and MSI prerequisites are verified; Linux uses OpenRGB. Manual 'openrgb' includes Corsair, 'icue' controls only Corsair on Windows, 'mystic' selects experimental MSI on Windows. Backend changes require restart; UI offers Apply and restart. Read get_pc_setup first; do not switch a user's backend just to change colors. MSI is untested on physical hardware, static RGB/brightness/power only. Official SDK can be prepared automatically when both MSI hardware and software evidence exist; actual SDK zones must be returned. mystic_light_dll is an advanced absolute official SDK override, normally unnecessary. Legacy mystic_light_enabled is retained for old clients; prefer pc_backend_mode."""
    params = {key: value for key, value in {
        "auto_start": auto_start,
        "minimize_to_tray": minimize_to_tray,
        "restore_scene": restore_scene,
        "mcp_auto_start": mcp_auto_start,
        "mcp_scope": mcp_scope,
        "language": language,
        "pc_backend_mode": pc_backend_mode,
        "mystic_light_enabled": mystic_light_enabled,
        "mystic_light_dll": mystic_light_dll,
    }.items() if value is not None}
    return await _call("settings_set", **params)


@mcp.tool(annotations=WRITE)
async def add_tapo_ip(ip: str) -> dict[str, Any]:
    """Aggiungi manualmente l'IP di una luce Tapo non trovata nella scansione LAN."""
    return await _call("settings_set", add_ip=ip)


class _LocalBearerAuth:
    """Keep the optional HTTP transport private to the desktop user."""

    def __init__(self, app, token: str, *, allowed_hosts=None, allowed_origins=None):
        self.app = app
        self.token = token.encode("ascii")
        self.allowed_hosts = {value.encode("ascii") for value in (allowed_hosts or [])}
        self.allowed_origins = {value.encode("ascii") for value in (allowed_origins or [])}

    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008})
            return
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            if self.allowed_hosts and headers.get(b"host", b"") not in self.allowed_hosts:
                await self._reject(send, 403)
                return
            origin = headers.get(b"origin")
            if origin and self.allowed_origins and origin not in self.allowed_origins:
                await self._reject(send, 403)
                return
            supplied = headers.get(b"authorization", b"")
            if not hmac.compare_digest(supplied, b"Bearer " + self.token):
                await self._reject(send, 401)
                return
        await self.app(scope, receive, send)

    @staticmethod
    async def _reject(send, status):
        body = b"Forbidden" if status == 403 else b"Unauthorized"
        await send({"type": "http.response.start", "status": status,
                    "headers": [(b"content-type", b"text/plain"),
                                (b"content-length", str(len(body)).encode())]})
        await send({"type": "http.response.body", "body": body})


def main() -> None:
    parser = argparse.ArgumentParser(description="Smartlight MCP server")
    parser.add_argument("--http", action="store_true", help="serve MCP on private loopback HTTP")
    parser.add_argument("--port", type=int, default=0, help="local MCP HTTP port")
    args = parser.parse_args()
    if not args.http:
        mcp.run(transport="stdio")
        return
    token = os.environ.get("SMARTLIGHT_MCP_TOKEN", "")
    if not token or not 1 <= args.port <= 65535:
        parser.error("HTTP requires a private token and a valid port")
    import uvicorn
    app = _LocalBearerAuth(mcp.streamable_http_app(
        streamable_http_path="/mcp", json_response=True,
        stateless_http=True, host="127.0.0.1"), token)
    config = uvicorn.Config(app, host="127.0.0.1", port=args.port,
                            log_level="error", access_log=False)
    uvicorn.Server(config).run()


if __name__ == "__main__":
    main()

