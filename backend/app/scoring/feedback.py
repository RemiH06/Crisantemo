"""Traduce score + features a retroalimentación en lenguaje llano.

Principio del proyecto: la puntuación se basa sobre todo en resonancia
(formantes), no en el tono. Esta capa existe para hacer ese punto visible a
quien practica, en vez de dejar que interprete el número solo. Nunca usa tono
de "aprobado/reprobado" (ver docs/ETHICS_PRIVACY.md). No es asesoría clínica:
las sugerencias son generales y no reemplazan a un logopeda o coach de voz.
"""

from __future__ import annotations

from acoustic_features import AcousticFeatures

# Rango de referencia amplio y solo orientativo, para poder comparar en el
# mensaje "tu tono por sí solo sugeriría X, pero tu resonancia pesa más".
# No es un umbral clínico ni el cálculo real del score (eso lo hace el modelo).
_PITCH_ONLY_FLOOR_HZ = 85.0
_PITCH_ONLY_CEILING_HZ = 260.0

# A partir de qué diferencia entre el score real y la referencia de "solo
# tono" vale la pena mencionar explícitamente el contraste tono/resonancia.
_PITCH_RESONANCE_GAP_THRESHOLD = 15.0

_LOW_HNR_DB = 10.0
_LOW_VOICED_SECONDS = 1.5


def _pitch_only_reference(f0_mean_hz: float) -> float:
    span = _PITCH_ONLY_CEILING_HZ - _PITCH_ONLY_FLOOR_HZ
    ratio = (f0_mean_hz - _PITCH_ONLY_FLOOR_HZ) / span
    return max(0.0, min(100.0, ratio * 100))


def _score_band(score: float) -> str:
    if score < 35:
        return "una percepción predominantemente masculina"
    if score > 65:
        return "una percepción predominantemente femenina"
    return "una percepción mixta o andrógina"


def build_feedback(score: float, features: AcousticFeatures) -> dict:
    pitch_only = _pitch_only_reference(features.f0_mean_hz)
    gap = score - pitch_only

    summary = f"Esta grabación puntuó {score:.1f}/100, {_score_band(score)}."
    suggestions: list[dict] = []

    if gap > _PITCH_RESONANCE_GAP_THRESHOLD:
        suggestions.append(
            {
                "kind": "acierto",
                "text": (
                    "Tu tono por sí solo sugeriría un puntaje más bajo, pero tu resonancia "
                    "(formantes) es lo que más está subiendo tu score. Es justo lo que "
                    "Crisantemo busca medir: no hace falta forzar un tono más agudo si la "
                    "resonancia ya está haciendo el trabajo."
                ),
            }
        )
    elif gap < -_PITCH_RESONANCE_GAP_THRESHOLD:
        suggestions.append(
            {
                "kind": "problema",
                "text": (
                    "Tu tono por sí solo sugeriría un puntaje más alto, pero tu resonancia "
                    "(formantes) todavía no lo acompaña."
                ),
            }
        )
        suggestions.append(
            {
                "kind": "sugerencia",
                "text": (
                    "Antes de subir más el tono, vale más la pena trabajar la resonancia "
                    "(colocación de la voz más adelante, ejercicios de humming); forzar un "
                    "tono agudo sin ese trabajo puede cansar la voz sin mover mucho el score."
                ),
            }
        )

    if features.hnr_db < _LOW_HNR_DB:
        suggestions.append(
            {
                "kind": "advertencia",
                "text": (
                    "La claridad de la voz (relación armónico-ruido) salió baja en esta "
                    "grabación; puede ser ruido de fondo o una voz más soplada de lo usual. "
                    "Vale la pena repetir la grabación en un lugar más silencioso."
                ),
            }
        )

    if features.voiced_seconds < _LOW_VOICED_SECONDS:
        suggestions.append(
            {
                "kind": "advertencia",
                "text": (
                    "Se detectó poca voz sonora en la grabación; una toma un poco más larga "
                    "da un análisis más estable."
                ),
            }
        )

    if not suggestions:
        suggestions.append(
            {
                "kind": "sugerencia",
                "text": (
                    "Sigue practicando con grabaciones variadas para ver qué tan consistente "
                    "se mantiene tu resonancia."
                ),
            }
        )

    return {"summary": summary, "tone": "supportive", "suggestions": suggestions}
