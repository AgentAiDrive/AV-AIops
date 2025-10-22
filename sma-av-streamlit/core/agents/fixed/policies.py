# policies.py — Fixed Agent Policy Definitions

from enum import Enum
from datetime import time

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class MaintenanceWindow:
    def __init__(self, name, start_hour, end_hour, days):
        self.name = name
        self.start_time = time(start_hour)
        self.end_time = time(end_hour)
        self.days = days  # List of integers 0=Mon ... 6=Sun

    def is_within_window(self, check_time):
        return (
            check_time.weekday() in self.days and
            self.start_time <= check_time.time() <= self.end_time
        )

STANDARD_MAINTENANCE = MaintenanceWindow(
    name="standard",
    start_hour=2,
    end_hour=5,
    days=[6, 0]  # Sunday and Monday
)

class RBACRoles(str, Enum):
    SUPPORT = "support"
    ADMIN = "admin"
    BUILDS = "builds"
    AUDITOR = "auditor"

# Policy Map by Agent
FIXED_AGENT_POLICIES = {
    "BaselineAgent": {
        "risk_level": RiskLevel.LOW,
        "allowed_roles": [RBACRoles.ADMIN, RBACRoles.BUILDS],
        "maintenance_window": STANDARD_MAINTENANCE
    },
    "PlanAgent": {
        "risk_level": RiskLevel.MEDIUM,
        "allowed_roles": [RBACRoles.SUPPORT, RBACRoles.ADMIN],
        "maintenance_window": STANDARD_MAINTENANCE
    },
    "ActAgent": {
        "risk_level": RiskLevel.HIGH,
        "allowed_roles": [RBACRoles.ADMIN],
        "maintenance_window": STANDARD_MAINTENANCE
    },
    "VerifyAgent": {
        "risk_level": RiskLevel.LOW,
        "allowed_roles": [RBACRoles.SUPPORT, RBACRoles.AUDITOR],
        "maintenance_window": STANDARD_MAINTENANCE
    },
    "LearnAgent": {
        "risk_level": RiskLevel.LOW,
        "allowed_roles": [RBACRoles.SUPPORT, RBACRoles.ADMIN],
        "maintenance_window": STANDARD_MAINTENANCE
    },
    "IntakeAgent": {
        "risk_level": RiskLevel.LOW,
        "allowed_roles": [RBACRoles.SUPPORT],
        "maintenance_window": STANDARD_MAINTENANCE
    }
}
