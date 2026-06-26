"""Wrapper YOLOv8/v10 (ultralytics). Carrega .pt e expõe `detectar_crianca_sozinha`.

A regra "criança sozinha" = detecta pelo menos 1 classe `crianca` (ou `child`)
e NENHUMA classe `adulto`/`adult`/`person_adult` no frame.

Ajuste os nomes das classes conforme o seu dataset/treinamento.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)

CLASSES_CRIANCA = {"crianca", "child", "kid", "baby"}
CLASSES_ADULTO = {"adulto", "adult", "person_adult"}


class DetectorYOLO:
    def __init__(self, modelo_path: str | None = None, conf: float | None = None) -> None:
        s = get_settings()
        self.modelo_path = Path(modelo_path or s.yolo_model_path)
        self.conf = conf if conf is not None else s.yolo_conf_threshold
        self._modelo: Any = None  # carregamento lazy

    def _carregar(self) -> Any:
        if self._modelo is not None:
            return self._modelo
        if not self.modelo_path.exists():
            raise FileNotFoundError(
                f"Modelo YOLO não encontrado em {self.modelo_path}. "
                "Coloque seu .pt em /modelos e ajuste YOLO_MODEL_PATH."
            )
        from ultralytics import YOLO  # import lazy para acelerar boot
        logger.info("Carregando modelo YOLO: %s", self.modelo_path)
        self._modelo = YOLO(str(self.modelo_path))
        return self._modelo

    def detectar_crianca_sozinha(self, imagem) -> bool:
        """`imagem` pode ser path, numpy array (BGR) ou PIL.Image."""
        modelo = self._carregar()
        resultados = modelo.predict(source=imagem, conf=self.conf, verbose=False)

        tem_crianca = False
        tem_adulto = False
        for r in resultados:
            nomes = r.names  # dict {id: nome}
            for box in r.boxes:
                cls_id = int(box.cls.item())
                nome = (nomes.get(cls_id, "") or "").lower()
                if nome in CLASSES_CRIANCA:
                    tem_crianca = True
                elif nome in CLASSES_ADULTO:
                    tem_adulto = True
        return tem_crianca and not tem_adulto
