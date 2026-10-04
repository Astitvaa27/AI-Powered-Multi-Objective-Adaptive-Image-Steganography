"""
Adaptive multi-objective embedding (closed loop).

    cover image + payload
        -> candidate grid (LSB per channel mode / bit depth, DCT, DWT)
        -> capacity check            (candidates that cannot fit are skipped)
        -> embed every remaining candidate
        -> round-trip extraction     (hard constraint: must match exactly)
        -> PSNR / SSIM / MSE and sample modification rate
        -> robustness probe          (JPEG re-encode, then extract)
        -> steganalysis              (Random Forest P(STEGO))
        -> normalised objectives, weighted-sum score, Pareto check
        -> best candidate

How the selection works
-----------------------
Every feasible candidate gets five objective scores in [0, 1], where 1 is
always better:

    quality     = 0.5 * clip((PSNR - PSNR_FLOOR) / (PSNR_CEILING - PSNR_FLOOR))
                + 0.5 * clip((SSIM - SSIM_FLOOR) / (1 - SSIM_FLOOR))
    distortion  = 1 - clip(change_rate / CHANGE_RATE_CEILING)
    capacity    = 1 - payload_bytes / capacity_bytes      (headroom)
    security    = 1 - P(STEGO)                             (steganalysis)
    robustness  = clip(2 * bit_accuracy_after_jpeg - 1)    (0 = chance level)

    score = sum(weight[o] * objective[o]  for o in measured objectives)

The weights come from settings (or a per-request override) and are
renormalised over the objectives that could actually be measured. The
candidate with the highest score is selected. Scores within
ADAPTIVE_SCORE_TIE_TOLERANCE of the best are treated as a tie, broken by
lower P(stego), then higher raw PSNR, then grid order. A Pareto-optimality
flag is reported for every candidate so the trade-offs are visible.

This is an exhaustive search over a small discrete candidate grid scored
with a weighted sum. It is not a metaheuristic or learned optimiser.

Normalisation uses fixed, documented reference ranges rather than min-max
scaling across candidates, so a tiny SSIM difference (0.99998 vs 0.99997)
is not stretched into a 0-vs-1 gap.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from uuid import UUID

import numpy as np
from PIL import Image as PILImage
from sqlalchemy.orm import Session

from backend.app.config import Settings
from backend.app.models.candidate_configuration import CandidateConfiguration
from backend.app.models.embedding_method import EmbeddingMethod
from backend.app.models.objective_score import ObjectiveScore
from backend.app.models.optimization_iteration import OptimizationIteration
from backend.app.models.optimization_run import OptimizationRun
from backend.app.services.embedding_service import (
    SUPPORTED_METHODS,
    calculate_method_capacity,
    embed_with_method,
    extract_with_method,
)
from backend.app.services.metrics_service import (
    calculate_change_statistics,
    calculate_metrics,
)


OBJECTIVES = ("quality", "security", "distortion", "capacity", "robustness")

OPTIMIZATION_ALGORITHM = "EXHAUSTIVE_WEIGHTED_SUM"
OBJECTIVE_FUNCTION = "ADAPTIVE_MULTI_OBJECTIVE"
WEIGHTED_SUM_OBJECTIVE = "WEIGHTED_SUM"


class AdaptiveSelectionError(ValueError):
    """Raised when no candidate can carry the payload."""

    def __init__(self, message: str, candidates: list[dict]):
        super().__init__(message)
        self.candidates = candidates


@dataclass(frozen=True)
class CandidateSpec:
    method: str
    channel_mode: str = "RGB"
    lsb_bits: int = 1

    @property
    def key(self) -> str:
        if self.method == "LSB":
            return f"LSB-{self.channel_mode}-{self.lsb_bits}"
        return self.method

    @property
    def label(self) -> str:
        if self.method == "LSB":
            return f"LSB ({self.channel_mode}, {self.lsb_bits}-bit)"
        return {
            "DCT": "DCT (blue channel, 8x8 blocks)",
            "DWT": "DWT (blue channel, Haar HH band)",
        }.get(self.method, self.method)

    @property
    def parameters(self) -> dict:
        if self.method == "LSB":
            return {
                "channel_mode": self.channel_mode,
                "lsb_bits": self.lsb_bits,
            }
        return {}


@dataclass
class AdaptiveEvaluation:
    candidates: list[dict]
    selected: dict
    weights: dict[str, float]
    objectives_evaluated: list[str]
    cover_stego_probability: float | None
    steganalysis_available: bool
    steganalysis_error: str | None
    explanation: list[str]
    limitations: list[str]
    processing_time_ms: int
    selected_output_path: str
    configuration: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def build_candidate_grid(
    settings: Settings,
    disabled_methods: set[str] | None = None,
) -> list[CandidateSpec]:
    """Expand the configured grid, leaving out deactivated methods."""

    disabled = {code.upper() for code in (disabled_methods or set())}
    grid: list[CandidateSpec] = []

    if "LSB" not in disabled:
        for channel_mode in settings.ADAPTIVE_LSB_CHANNEL_MODES:
            for lsb_bits in settings.ADAPTIVE_LSB_BITS:
                grid.append(
                    CandidateSpec(
                        method="LSB",
                        channel_mode=channel_mode.upper(),
                        lsb_bits=int(lsb_bits),
                    )
                )

    for method in ("DCT", "DWT"):
        if method not in disabled:
            grid.append(CandidateSpec(method=method))

    return grid


def resolve_weights(
    settings: Settings,
    overrides: dict[str, float] | None = None,
) -> dict[str, float]:
    """Merge per-request overrides with configured weights and normalise."""

    weights = {
        "quality": settings.ADAPTIVE_WEIGHT_QUALITY,
        "security": settings.ADAPTIVE_WEIGHT_SECURITY,
        "distortion": settings.ADAPTIVE_WEIGHT_DISTORTION,
        "capacity": settings.ADAPTIVE_WEIGHT_CAPACITY,
        "robustness": settings.ADAPTIVE_WEIGHT_ROBUSTNESS,
    }

    for name, value in (overrides or {}).items():
        if name not in weights:
            raise ValueError(
                f"Unknown objective '{name}'. Valid objectives: "
                + ", ".join(OBJECTIVES)
            )
        weights[name] = float(value)

    if any(value < 0 for value in weights.values()):
        raise ValueError("Objective weights must be non-negative.")

    total = sum(weights.values())

    if total <= 0:
        raise ValueError("At least one objective weight must be positive.")

    return {name: value / total for name, value in weights.items()}


# ---------------------------------------------------------------------------
# Measurement helpers
# ---------------------------------------------------------------------------


def _clip(value: float) -> float:
    return float(min(1.0, max(0.0, value)))


def _bit_accuracy(expected: bytes, recovered: bytes) -> float:
    """Fraction of payload bits recovered correctly (missing bits count wrong)."""

    expected_bits = np.unpackbits(np.frombuffer(expected, dtype=np.uint8))

    if expected_bits.size == 0:
        return 1.0

    recovered_bits = np.unpackbits(
        np.frombuffer(recovered[:len(expected)], dtype=np.uint8)
    )

    matches = int(
        np.count_nonzero(
            expected_bits[:recovered_bits.size] == recovered_bits
        )
    )

    return matches / expected_bits.size


class _SteganalysisProbe:
    """
    Thin wrapper around the existing Random Forest steganalysis pipeline.

    It uses exactly the feature extractor and classifier that the
    /steganalysis endpoints use, so the probability reported for a
    candidate matches what a later steganalysis run on the same image
    returns.
    """

    def __init__(self):
        self.available = False
        self.error: str | None = None
        self._loaded_model: tuple | None = None

        try:
            from backend.app.services.steganalysis_ml_service import (
                load_random_forest,
            )

            self._loaded_model = load_random_forest()
            self.available = True
        except Exception as exc:  # model file missing / unreadable
            self.error = f"Steganalysis model unavailable: {exc}"

    def predict(self, image_path: str) -> dict:
        from backend.app.services.steganalysis_ml_service import (
            predict_steganography,
        )
        from backend.app.services.steganalysis_service import (
            extract_statistical_features,
        )

        prediction = predict_steganography(
            extract_statistical_features(image_path),
            loaded_model=self._loaded_model,
        )

        probabilities = prediction["probabilities"]

        if "STEGO" not in probabilities:
            raise ValueError(
                "Steganalysis model does not expose a STEGO class probability."
            )

        return {
            "stego_probability": float(probabilities["STEGO"]),
            "predicted_class": prediction["predicted_class"],
        }


def _empty_candidate(spec: CandidateSpec, payload_size: int) -> dict:
    return {
        "key": spec.key,
        "label": spec.label,
        "method": spec.method,
        "parameters": spec.parameters,
        "status": "PENDING",
        "feasible": False,
        "failure_reason": None,
        "payload_size_bytes": payload_size,
        "capacity_bytes": None,
        "capacity_used_ratio": None,
        "extraction_verified": None,
        "mse": None,
        "psnr": None,
        "ssim": None,
        "change_rate": None,
        "max_abs_change": None,
        "stego_probability": None,
        "steganalysis_class": None,
        "robustness_bit_accuracy": None,
        "objectives": {},
        "score": None,
        "rank": None,
        "pareto_optimal": None,
        "selected": False,
        "processing_time_ms": None,
    }


def _evaluate_candidate(
    spec: CandidateSpec,
    cover_path: str,
    cover_image: PILImage.Image,
    payload: bytes,
    work_dir: Path,
    probe: _SteganalysisProbe,
    settings: Settings,
) -> tuple[dict, str | None]:
    """Embed, verify and measure one candidate. Never raises."""

    result = _empty_candidate(spec, len(payload))
    started = perf_counter()
    output_path = work_dir / f"{spec.key}.png"

    try:
        capacity = calculate_method_capacity(
            spec.method,
            cover_image,
            spec.channel_mode,
            spec.lsb_bits,
        )
        result["capacity_bytes"] = capacity
        result["capacity_used_ratio"] = (
            len(payload) / capacity if capacity else None
        )

        if len(payload) > capacity:
            result["status"] = "SKIPPED"
            result["failure_reason"] = (
                f"Payload ({len(payload)} B) exceeds capacity "
                f"({capacity} B)."
            )
            return result, None

        embed_result = embed_with_method(
            spec.method,
            cover_path,
            str(output_path),
            payload,
            spec.channel_mode,
            spec.lsb_bits,
        )

        # Trust the embedder's own figure if it differs from the estimate.
        capacity = embed_result.get("capacity_bytes", capacity)
        result["capacity_bytes"] = capacity
        result["capacity_used_ratio"] = (
            len(payload) / capacity if capacity else None
        )

        try:
            recovered = extract_with_method(
                spec.method,
                str(output_path),
                spec.channel_mode,
                spec.lsb_bits,
            )
        except ValueError:
            recovered = b""

        result["extraction_verified"] = recovered == payload

        metrics = calculate_metrics(cover_path, str(output_path))
        changes = calculate_change_statistics(cover_path, str(output_path))

        result["mse"] = metrics["mse"]
        result["psnr"] = (
            None if metrics["psnr"] == float("inf") else metrics["psnr"]
        )
        result["ssim"] = metrics["ssim"]
        result["change_rate"] = changes["change_rate"]
        result["max_abs_change"] = changes["max_abs_change"]

        if not result["extraction_verified"]:
            result["status"] = "REJECTED"
            result["failure_reason"] = (
                "Round-trip extraction did not reproduce the payload, so this "
                "stego image would lose data."
            )
            return result, None

        if settings.ADAPTIVE_ROBUSTNESS_ENABLED:
            jpeg_path = work_dir / f"{spec.key}_jpeg.jpg"

            with PILImage.open(output_path) as stego_image:
                stego_image.convert("RGB").save(
                    jpeg_path,
                    format="JPEG",
                    quality=settings.ADAPTIVE_ROBUSTNESS_JPEG_QUALITY,
                )

            try:
                survived = extract_with_method(
                    spec.method,
                    str(jpeg_path),
                    spec.channel_mode,
                    spec.lsb_bits,
                )
            except Exception:
                # The length header was destroyed: nothing is recoverable.
                survived = b""

            result["robustness_bit_accuracy"] = _bit_accuracy(
                payload,
                survived,
            )

        if probe.available:
            detection = probe.predict(str(output_path))
            result["stego_probability"] = detection["stego_probability"]
            result["steganalysis_class"] = detection["predicted_class"]

        result["status"] = "EVALUATED"
        result["feasible"] = True

        return result, str(output_path)

    except Exception as exc:
        result["status"] = "FAILED"
        result["failure_reason"] = str(exc) or exc.__class__.__name__
        return result, None

    finally:
        result["processing_time_ms"] = int((perf_counter() - started) * 1000)


def _objective_scores(candidate: dict, settings: Settings) -> dict[str, float]:
    psnr = candidate["psnr"]

    psnr_score = (
        1.0
        if psnr is None  # identical images -> infinite PSNR
        else _clip(
            (psnr - settings.ADAPTIVE_PSNR_FLOOR_DB)
            / (settings.ADAPTIVE_PSNR_CEILING_DB - settings.ADAPTIVE_PSNR_FLOOR_DB)
        )
    )

    ssim_score = _clip(
        (candidate["ssim"] - settings.ADAPTIVE_SSIM_FLOOR)
        / (1.0 - settings.ADAPTIVE_SSIM_FLOOR)
    )

    objectives = {
        "quality": 0.5 * psnr_score + 0.5 * ssim_score,
        "distortion": 1.0 - _clip(
            candidate["change_rate"] / settings.ADAPTIVE_CHANGE_RATE_CEILING
        ),
        "capacity": 1.0 - _clip(candidate["capacity_used_ratio"] or 0.0),
    }

    if candidate["stego_probability"] is not None:
        objectives["security"] = 1.0 - _clip(candidate["stego_probability"])

    if candidate["robustness_bit_accuracy"] is not None:
        objectives["robustness"] = _clip(
            2.0 * candidate["robustness_bit_accuracy"] - 1.0
        )

    return objectives


def _dominates(a: dict[str, float], b: dict[str, float], names: list[str]) -> bool:
    return all(a[n] >= b[n] for n in names) and any(a[n] > b[n] for n in names)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def evaluate_adaptive_candidates(
    cover_path: str,
    payload: bytes,
    work_dir: Path,
    settings: Settings,
    weights: dict[str, float],
    grid: list[CandidateSpec],
) -> AdaptiveEvaluation:
    """
    Run the full closed loop over the candidate grid and pick the best
    candidate. Candidate stego images are written into work_dir; the
    caller is responsible for persisting the selected one.
    """

    started = perf_counter()

    if not grid:
        raise AdaptiveSelectionError(
            "No embedding methods are enabled for adaptive selection.",
            [],
        )

    try:
        with PILImage.open(cover_path) as opened:
            cover_image = opened.convert("RGB")
    except Exception as exc:
        raise ValueError(f"Unsupported or corrupted cover image: {exc}")

    probe = _SteganalysisProbe()

    cover_stego_probability = None

    if probe.available:
        try:
            cover_stego_probability = probe.predict(cover_path)[
                "stego_probability"
            ]
        except Exception as exc:
            probe.available = False
            probe.error = f"Steganalysis failed on the cover image: {exc}"

    candidates: list[dict] = []
    output_paths: dict[str, str] = {}

    for spec in grid:
        candidate, output_path = _evaluate_candidate(
            spec,
            cover_path,
            cover_image,
            payload,
            work_dir,
            probe,
            settings,
        )
        candidates.append(candidate)

        if output_path:
            output_paths[spec.key] = output_path

    feasible = [c for c in candidates if c["feasible"]]

    if not feasible:
        reasons = "; ".join(
            f"{c['label']}: {c['failure_reason'].rstrip('.')}"
            for c in candidates
        )
        raise AdaptiveSelectionError(
            f"No candidate could embed the payload. {reasons}.",
            candidates,
        )

    # Objectives are scored only if they were measured for every feasible
    # candidate, so all candidates are compared on the same basis.
    for candidate in feasible:
        candidate["objectives"] = _objective_scores(candidate, settings)

    measured = [
        name
        for name in OBJECTIVES
        if all(name in c["objectives"] for c in feasible)
    ]

    active_weight_total = sum(weights[name] for name in measured)

    if active_weight_total <= 0:
        raise AdaptiveSelectionError(
            "All measurable objectives have zero weight; nothing to optimise.",
            candidates,
        )

    effective_weights = {
        name: (weights[name] / active_weight_total if name in measured else 0.0)
        for name in OBJECTIVES
    }

    for candidate in feasible:
        candidate["objectives"] = {
            name: candidate["objectives"][name] for name in measured
        }
        candidate["score"] = sum(
            effective_weights[name] * candidate["objectives"][name]
            for name in measured
        )

    for candidate in feasible:
        candidate["pareto_optimal"] = not any(
            _dominates(other["objectives"], candidate["objectives"], measured)
            for other in feasible
            if other is not candidate
        )

    grid_order = {c["key"]: index for index, c in enumerate(candidates)}

    def tie_break(c: dict) -> tuple:
        psnr = c["psnr"] if c["psnr"] is not None else float("inf")
        return (
            -c["objectives"].get("security", 0.0),
            -psnr,
            grid_order[c["key"]],
        )

    best_score = max(c["score"] for c in feasible)
    tolerance = settings.ADAPTIVE_SCORE_TIE_TOLERANCE

    tied = sorted(
        [c for c in feasible if best_score - c["score"] <= tolerance],
        key=tie_break,
    )
    rest = sorted(
        [c for c in feasible if best_score - c["score"] > tolerance],
        key=lambda c: (-c["score"], *tie_break(c)),
    )

    ranked = tied + rest

    for rank, candidate in enumerate(ranked, start=1):
        candidate["rank"] = rank

    selected = ranked[0]
    selected["selected"] = True

    limitations = _limitations(probe, settings, measured)
    explanation = _explain(
        candidates,
        ranked,
        effective_weights,
        measured,
        cover_stego_probability,
        tied_count=len(tied),
        tolerance=tolerance,
    )

    return AdaptiveEvaluation(
        candidates=candidates,
        selected=selected,
        weights=effective_weights,
        objectives_evaluated=measured,
        cover_stego_probability=cover_stego_probability,
        steganalysis_available=probe.available,
        steganalysis_error=probe.error,
        explanation=explanation,
        limitations=limitations,
        processing_time_ms=int((perf_counter() - started) * 1000),
        selected_output_path=output_paths[selected["key"]],
        configuration={
            "algorithm": OPTIMIZATION_ALGORITHM,
            "requested_weights": weights,
            "candidate_grid": [
                {"key": spec.key, "method": spec.method, **spec.parameters}
                for spec in grid
            ],
            "normalisation": {
                "psnr_floor_db": settings.ADAPTIVE_PSNR_FLOOR_DB,
                "psnr_ceiling_db": settings.ADAPTIVE_PSNR_CEILING_DB,
                "ssim_floor": settings.ADAPTIVE_SSIM_FLOOR,
                "change_rate_ceiling": settings.ADAPTIVE_CHANGE_RATE_CEILING,
            },
            "robustness": {
                "enabled": settings.ADAPTIVE_ROBUSTNESS_ENABLED,
                "attack": "JPEG re-encode",
                "jpeg_quality": settings.ADAPTIVE_ROBUSTNESS_JPEG_QUALITY,
            },
        },
    )


def _limitations(
    probe: _SteganalysisProbe,
    settings: Settings,
    measured: list[str],
) -> list[str]:
    notes = []

    if probe.available:
        notes.append(
            "Detectability comes from the project's Random Forest classifier, "
            "which is trained on LSB-domain statistics (LSB ratios, pair "
            "rates, RS analysis). It is largely blind to DCT/DWT changes, so "
            "a low P(stego) for those methods means this detector cannot see "
            "them, not that they are undetectable in general."
        )
        notes.append(
            "P(stego) also depends on the cover itself; compare each "
            "candidate with the unmodified cover's baseline probability."
        )
    else:
        notes.append(
            (probe.error or "Steganalysis model unavailable.")
            + " The security objective was excluded and its weight "
            "redistributed over the remaining objectives."
        )

    if not settings.ADAPTIVE_ROBUSTNESS_ENABLED or "robustness" not in measured:
        notes.append("Robustness was not measured for this run.")
    else:
        notes.append(
            "Robustness is measured against a single attack (JPEG re-encode "
            f"at quality {settings.ADAPTIVE_ROBUSTNESS_JPEG_QUALITY}). "
            "Stego images are delivered as lossless PNG, so this only matters "
            "if the image will be recompressed downstream."
        )

    return notes


def _explain(
    candidates: list[dict],
    ranked: list[dict],
    weights: dict[str, float],
    measured: list[str],
    cover_stego_probability: float | None,
    tied_count: int,
    tolerance: float,
) -> list[str]:
    selected = ranked[0]
    methods = sorted({c["method"] for c in candidates}, key=SUPPORTED_METHODS.index)

    lines = [
        f"Evaluated {len(candidates)} candidate configurations across "
        f"{', '.join(methods)}; {len(ranked)} embedded the payload and passed "
        "round-trip extraction.",
    ]

    for candidate in candidates:
        if not candidate["feasible"]:
            lines.append(
                f"{candidate['label']} was {candidate['status'].lower()}: "
                f"{candidate['failure_reason']}"
            )

    weight_text = ", ".join(
        f"{name} {weights[name]:.0%}" for name in measured if weights[name] > 0
    )
    lines.append(f"Objective weights used: {weight_text}.")

    if len(ranked) > 1:
        runner_up = ranked[1]
        margin = selected["score"] - runner_up["score"]
        advantages = [
            name
            for name in measured
            if selected["objectives"][name] - runner_up["objectives"][name] > 0.005
        ]
        if tied_count > 1:
            lead = (
                f"Selected {selected['label']} (score {selected['score']:.3f}) "
                f"over {runner_up['label']} ({runner_up['score']:.3f}) on the "
                "tie-break"
            )
        else:
            lead = (
                f"Selected {selected['label']} with score "
                f"{selected['score']:.3f}, ahead of {runner_up['label']} "
                f"({runner_up['score']:.3f}, margin {margin:.3f})"
            )
        lines.append(
            lead
            + (
                f"; it scores higher on {', '.join(advantages)}."
                if advantages
                else "."
            )
        )
    else:
        lines.append(
            f"Selected {selected['label']} as the only feasible candidate "
            f"(score {selected['score']:.3f})."
        )

    if tied_count > 1:
        lines.append(
            f"{tied_count} candidates scored within {tolerance:.3f} of the best "
            "score, which is treated as a tie; the tie was broken by lower "
            "steganalysis P(stego), then higher PSNR."
        )

    if selected["pareto_optimal"]:
        lines.append(
            "The selected candidate is Pareto-optimal: no other candidate is "
            "at least as good on every objective and better on one."
        )
    else:
        lines.append(
            "Another tied candidate is marginally better on every objective, "
            "but by less than the tie tolerance; see the comparison table."
        )

    if selected["stego_probability"] is not None and cover_stego_probability is not None:
        delta = selected["stego_probability"] - cover_stego_probability
        lines.append(
            f"Steganalysis P(stego) for the selected image is "
            f"{selected['stego_probability']:.3f} versus "
            f"{cover_stego_probability:.3f} for the unmodified cover "
            f"({delta:+.3f})."
        )

    return lines


# ---------------------------------------------------------------------------
# Persistence into the existing optimisation tables
# ---------------------------------------------------------------------------


def persist_adaptive_run(
    db: Session,
    user_id: UUID,
    cover_image_id: UUID,
    payload_id: UUID,
    evaluation: AdaptiveEvaluation,
    selected_stego_image_id: UUID,
) -> tuple[OptimizationRun, OptimizationIteration]:
    """
    Record the run in optimization_runs / optimization_iterations /
    candidate_configurations / objective_scores. The full candidate
    comparison is kept in the iteration's optimizer_state so it can be
    returned again later without recomputation.

    Candidate rows need an embedding_methods row; methods that are not
    registered in the database are still evaluated and appear in
    optimizer_state, but get no candidate_configurations row.

    The caller commits.
    """

    now = datetime.now(timezone.utc)

    run = OptimizationRun(
        user_id=user_id,
        image_id=cover_image_id,
        payload_id=payload_id,
        optimization_algorithm=OPTIMIZATION_ALGORITHM,
        objective_function=OBJECTIVE_FUNCTION,
        max_iterations=1,
        status="COMPLETED",
        best_score=evaluation.selected["score"],
        processing_time_ms=evaluation.processing_time_ms,
        configuration=evaluation.configuration,
        started_at=now,
        completed_at=now,
    )
    db.add(run)
    db.flush()

    iteration = OptimizationIteration(
        optimization_run_id=run.id,
        iteration_number=1,
        status="COMPLETED",
        optimizer_state={},
        started_at=now,
        completed_at=now,
    )
    db.add(iteration)
    db.flush()

    methods = {
        method.code: method
        for method in db.query(EmbeddingMethod)
        .filter(EmbeddingMethod.code.in_(SUPPORTED_METHODS))
        .all()
    }

    for number, candidate in enumerate(evaluation.candidates, start=1):
        method = methods.get(candidate["method"])

        if not method:
            continue

        row = CandidateConfiguration(
            iteration_id=iteration.id,
            method_id=method.id,
            candidate_number=number,
            parameters=candidate["parameters"],
            status="COMPLETED" if candidate["feasible"] else candidate["status"],
        )
        db.add(row)
        db.flush()

        candidate["candidate_id"] = str(row.id)

        if candidate["selected"]:
            run.selected_candidate_id = row.id
            iteration.selected_candidate_id = row.id

        if not candidate["feasible"]:
            continue

        metric_values = {
            key: candidate[key]
            for key in (
                "psnr",
                "ssim",
                "mse",
                "change_rate",
                "max_abs_change",
                "capacity_bytes",
                "payload_size_bytes",
                "capacity_used_ratio",
                "stego_probability",
                "robustness_bit_accuracy",
            )
        }

        if candidate["selected"]:
            metric_values["stego_image_id"] = str(selected_stego_image_id)

        for name, value in candidate["objectives"].items():
            db.add(
                ObjectiveScore(
                    candidate_configuration_id=row.id,
                    objective_name=name.upper(),
                    score=value,
                    metric_values=metric_values,
                    ranking=None,
                )
            )

        db.add(
            ObjectiveScore(
                candidate_configuration_id=row.id,
                objective_name=WEIGHTED_SUM_OBJECTIVE,
                score=candidate["score"],
                metric_values={
                    **metric_values,
                    "weights": evaluation.weights,
                    "pareto_optimal": candidate["pareto_optimal"],
                },
                ranking=candidate["rank"],
            )
        )

    iteration.optimizer_state = build_comparison_payload(evaluation)

    return run, iteration


def build_comparison_payload(evaluation: AdaptiveEvaluation) -> dict:
    """JSON-safe description of the run, shared by the API and storage."""

    return {
        "algorithm": OPTIMIZATION_ALGORITHM,
        "selected_method": evaluation.selected["method"],
        "selected_candidate_key": evaluation.selected["key"],
        "selected_parameters": evaluation.selected["parameters"],
        "weights": evaluation.weights,
        "objectives_evaluated": evaluation.objectives_evaluated,
        "cover_stego_probability": evaluation.cover_stego_probability,
        "steganalysis_available": evaluation.steganalysis_available,
        "candidates": evaluation.candidates,
        "explanation": evaluation.explanation,
        "limitations": evaluation.limitations,
        "evaluation_time_ms": evaluation.processing_time_ms,
    }
