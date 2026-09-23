"""Deterministic HackMatrix detection rules."""

from .privilege_change import PrivilegeChangeRule

__all__ = ["PrivilegeChangeRule"]