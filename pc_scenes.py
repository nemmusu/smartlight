"""Built-in PC RGB scenes migrated from the user-provided HWLight project."""

SCENES = (
    ("sc_arcobaleno", "Arcobaleno", {
        "*": {"effect": "arcobaleno", "speed": 1.0, "brightness": 100},
    }),
    ("sc_ghiaccio", "Ghiaccio", {
        "Raffreddamento": {"effect": "onda", "color": [0, 210, 255], "color2": [0, 40, 255], "speed": 0.8},
        "Memoria": {"effect": "respiro", "color": [0, 150, 255], "speed": 0.6},
        "Periferiche": {"effect": "onda", "color": [0, 210, 255], "color2": [0, 40, 255], "speed": 0.6},
        "*": {"effect": "statico", "color": [0, 110, 255], "brightness": 100},
    }),
    ("sc_camino", "Camino", {
        "*": {"effect": "fuoco", "speed": 1.0, "brightness": 100},
    }),
    ("sc_aurora", "Aurora boreale", {
        "*": {"effect": "aurora", "color": [0, 120, 255], "color2": [160, 0, 255], "speed": 0.7, "brightness": 100},
    }),
    ("sc_matrix", "Matrix", {
        "Raffreddamento": {"effect": "cometa", "color": [0, 255, 90], "speed": 1.6},
        "Memoria": {"effect": "scintille", "color": [0, 255, 90], "speed": 1.2},
        "Periferiche": {"effect": "pioggia", "color": [0, 45, 10], "color2": [0, 255, 90], "speed": 1.4},
        "*": {"effect": "statico", "color": [0, 120, 40], "brightness": 100},
    }),
    ("sc_tramonto", "Tramonto", {
        "*": {"effect": "onda", "color": [255, 90, 0], "color2": [255, 0, 130], "speed": 0.5, "brightness": 100},
    }),
    ("sc_tempesta", "Tempesta", {
        "*": {"effect": "lampi", "color": [30, 60, 160], "speed": 1.0, "brightness": 100},
    }),
    ("sc_notte", "Notte (tenue)", {
        "*": {"effect": "respiro", "color": [80, 0, 180], "speed": 0.4, "brightness": 25},
    }),
    ("sc_festa", "Festa", {
        "Raffreddamento": {"effect": "ciclo", "speed": 3.0},
        "Memoria": {"effect": "pulsazione", "color": [255, 0, 160], "color2": [0, 220, 255], "speed": 3.0},
        "Periferiche": {"effect": "arcobaleno", "speed": 3.0},
        "*": {"effect": "ciclo", "speed": 3.0, "brightness": 100},
    }),
)
