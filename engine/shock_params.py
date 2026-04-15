"""
ShockScenario dataclass — defines the Hormuz closure scenario parameters.
"""
from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    PARTIAL = "PARTIAL"          # Temporary disruption, swift re-routing possible
    MODERATE = "MODERATE"        # Weeks-long chokepoint; tanker detours add cost
    SEVERE = "SEVERE"            # Months-long effective closure; global supply crunch
    EXTREME = "EXTREME"          # Full, prolonged closure; structural supply destruction

    # Historical calibration note:
    #   PARTIAL  ≈ 2019 Gulf tanker attacks (+25% oil price spike, ~2 weeks)
    #   MODERATE ≈ Libya 2011 supply loss (+55% from baseline over 3 months)
    #   SEVERE   ≈ Russia-Ukraine 2022 (+85% from pre-war levels within 4 months)
    #   EXTREME  ≈ Modelled full Hormuz closure (20% global supply removed; +120%)


# Oil price multipliers relative to pre-shock baseline (Brisbane-calibrated).
# Derived from Russia-Ukraine 2022 data + historical Hormuz scenario literature.
_OIL_MULTIPLIERS = {
    Severity.PARTIAL: 1.25,
    Severity.MODERATE: 1.55,
    Severity.SEVERE: 1.85,
    Severity.EXTREME: 2.20,
}


@dataclass
class ShockScenario:
    duration_weeks: int
    severity: Severity
    scenario_name: str = ""

    # Optional overrides (leave None to use calibrated defaults)
    custom_oil_multiplier: float | None = None

    def get_oil_multiplier(self) -> float:
        """
        Return the oil price multiplier for this scenario.
        Custom override wins if supplied; otherwise uses calibrated defaults.
        """
        if self.custom_oil_multiplier is not None:
            return float(self.custom_oil_multiplier)
        return _OIL_MULTIPLIERS[self.severity]

    def __post_init__(self):
        if isinstance(self.severity, str):
            self.severity = Severity(self.severity.upper())
        if self.duration_weeks < 1:
            raise ValueError("duration_weeks must be >= 1")
        if self.duration_weeks > 52:
            raise ValueError("duration_weeks must be <= 52")

    # ------------------------------------------------------------------ #
    # Convenience constructors for the four canonical scenarios            #
    # ------------------------------------------------------------------ #
    @classmethod
    def partial_disruption(cls, duration_weeks: int = 4) -> "ShockScenario":
        return cls(
            duration_weeks=duration_weeks,
            severity=Severity.PARTIAL,
            scenario_name="Partial Disruption",
        )

    @classmethod
    def moderate_closure(cls, duration_weeks: int = 8) -> "ShockScenario":
        return cls(
            duration_weeks=duration_weeks,
            severity=Severity.MODERATE,
            scenario_name="Moderate Closure",
        )

    @classmethod
    def severe_closure(cls, duration_weeks: int = 16) -> "ShockScenario":
        return cls(
            duration_weeks=duration_weeks,
            severity=Severity.SEVERE,
            scenario_name="Severe Closure",
        )

    @classmethod
    def extreme_closure(cls, duration_weeks: int = 26) -> "ShockScenario":
        return cls(
            duration_weeks=duration_weeks,
            severity=Severity.EXTREME,
            scenario_name="Extreme Closure",
        )
