"""
Acknowledgment verification for Design Intent Layer plugin.
Verifies that Claude has acknowledged design constraints before modifying files.
"""

import re
from typing import Dict, Any, Optional, Tuple


class AcknowledgmentVerifier:
    """Verifies Claude's acknowledgment of design constraints."""

    ACKNOWLEDGMENT_PATTERNS = [
        r"i acknowledge the design intent",
        r"i acknowledge.*constraints",
        r"i understand the design constraints",
        r"i\s+have\s+read\s+.*design\s+note",
        r"i\s+will\s+respect\s+.*constraints",
    ]

    def __init__(self, note: Dict[str, Any], file_path: str):
        """
        Initialize verifier with note and file path.

        Args:
            note: The design note dictionary
            file_path: The file being modified
        """
        self.note = note
        self.file_path = file_path
        self.file_name = file_path.split('\\')[-1].split('/')[-1]  # Handle both path separators

    def verify(self, claude_message: Optional[str] = None) -> Tuple[bool, str]:
        """
        Verify if Claude has acknowledged the design constraints.

        For now, this is a placeholder that always returns True in non-blocking mode.
        In a full implementation, this would analyze Claude's previous message
        to check for explicit acknowledgment.

        Args:
            claude_message: Claude's message (if available for verification)

        Returns:
            (is_acknowledged, message) tuple
        """
        requires_acknowledgment = self.note.get('requiresAcknowledgment', True)

        if not requires_acknowledgment:
            # Note doesn't require explicit acknowledgment
            return True, "Note loaded and injected into context"

        # If we have a message to verify, check it
        if claude_message:
            is_acknowledged = self._check_acknowledgment(claude_message)
            if is_acknowledged:
                return True, "Acknowledgment verified"
            else:
                return False, "Acknowledgment not found in response"

        # For PreToolUse hook, we inject the requirement and trust the system
        # The actual verification would happen in a PostToolUse or Stop hook
        # For now, we inject the requirement and allow execution
        return True, "Acknowledgment requirement injected"

    def _check_acknowledgment(self, message: str) -> bool:
        """
        Check if message contains acknowledgment patterns.

        Args:
            message: The message to check

        Returns:
            True if acknowledgment found, False otherwise
        """
        message_lower = message.lower()

        # Check for acknowledgment patterns
        for pattern in self.ACKNOWLEDGMENT_PATTERNS:
            if re.search(pattern, message_lower):
                # Verify file is mentioned
                if self.file_name.lower() in message_lower:
                    return True

        # For critical notes, check if specific constraints are mentioned
        if self._is_critical_note():
            return self._check_constraint_enumeration(message_lower)

        return False

    def _is_critical_note(self) -> bool:
        """Check if note has critical constraints."""
        # Check for critical assumptions
        for assumption in self.note.get('assumptions', []):
            if assumption.get('severity') == 'critical':
                return True

        # Check for frozen sections
        if self.note.get('frozenSections', []):
            return True

        return False

    def _check_constraint_enumeration(self, message_lower: str) -> bool:
        """
        Check if Claude has enumerated specific constraints.

        Args:
            message_lower: Lowercased message

        Returns:
            True if constraints are mentioned, False otherwise
        """
        mentioned_constraints = 0
        total_critical_constraints = 0

        # Check assumptions
        for assumption in self.note.get('assumptions', []):
            if assumption.get('severity') == 'critical':
                total_critical_constraints += 1
                assumption_id = assumption['id'].lower()
                if assumption_id in message_lower:
                    mentioned_constraints += 1

        # Check frozen sections
        for frozen in self.note.get('frozenSections', []):
            total_critical_constraints += 1
            frozen_id = frozen['id'].lower()
            if frozen_id in message_lower:
                mentioned_constraints += 1
            # Also check if pattern is mentioned
            if 'pattern' in frozen:
                pattern = frozen['pattern'].lower()
                if pattern in message_lower:
                    mentioned_constraints += 1

        # Require at least 50% of critical constraints to be mentioned
        if total_critical_constraints == 0:
            return True

        return mentioned_constraints >= (total_critical_constraints / 2)

    def format_acknowledgment_requirement(self) -> str:
        """
        Format the acknowledgment requirement message for injection.

        Returns:
            Formatted string to inject into Claude's context
        """
        lines = []
        lines.append("=" * 80)
        lines.append("DESIGN INTENT NOTE DETECTED")
        lines.append("=" * 80)
        lines.append(f"\nFile: {self.file_path}\n")

        # Design Intent
        if 'designIntent' in self.note:
            intent = self.note['designIntent']
            lines.append("DESIGN INTENT:")
            if intent.get('purpose'):
                lines.append(f"  Purpose: {intent['purpose']}")
            if intent.get('keyDecisions'):
                lines.append("  Key Decisions:")
                for decision in intent['keyDecisions']:
                    lines.append(f"    - {decision}")
            if intent.get('rationale'):
                lines.append(f"  Rationale: {intent['rationale']}")
            lines.append("")

        # Assumptions
        if self.note.get('assumptions'):
            lines.append("ASSUMPTIONS (Must be maintained):")
            for assumption in self.note['assumptions']:
                severity = assumption.get('severity', 'medium').upper()
                lines.append(f"  [{severity}] {assumption['id']}: {assumption['text']}")
            lines.append("")

        # Constraints
        if self.note.get('constraints'):
            lines.append("CONSTRAINTS (Active requirements):")
            for constraint in self.note['constraints']:
                constraint_type = constraint.get('type', 'functional')
                lines.append(f"  [{constraint_type}] {constraint['id']}: {constraint['text']}")
                if constraint.get('reason'):
                    lines.append(f"      Reason: {constraint['reason']}")
            lines.append("")

        # Tradeoffs
        if self.note.get('tradeoffs'):
            lines.append("KNOWN TRADEOFFS (Intentional shortcuts):")
            for tradeoff in self.note['tradeoffs']:
                debt_level = tradeoff.get('debtLevel', 'medium').upper()
                lines.append(f"  [{debt_level}] {tradeoff['id']}: {tradeoff['shortcut']}")
                lines.append(f"      Reason: {tradeoff['reason']}")
                if tradeoff.get('repaymentPlan'):
                    lines.append(f"      Repayment Plan: {tradeoff['repaymentPlan']}")
            lines.append("")

        # Frozen Sections
        if self.note.get('frozenSections'):
            lines.append("FROZEN SECTIONS (DO NOT MODIFY):")
            for frozen in self.note['frozenSections']:
                lines.append(f"  {frozen['id']}:")
                if 'pattern' in frozen:
                    lines.append(f"      Pattern: {frozen['pattern']}")
                if 'lineRange' in frozen:
                    lines.append(f"      Lines: {frozen['lineRange'][0]}-{frozen['lineRange'][1]}")
                lines.append(f"      Reason: {frozen['reason']}")
                if frozen.get('exceptions'):
                    lines.append(f"      Exceptions: {frozen['exceptions']}")
            lines.append("")

        # Acknowledgment requirement
        lines.append("=" * 80)
        lines.append("ACKNOWLEDGMENT REQUIRED")
        lines.append("=" * 80)

        if self.note.get('requiresAcknowledgment', True):
            lines.append(f"\nYou MUST explicitly state:")
            lines.append(f'  "I acknowledge the design intent constraints for {self.file_name}"')
            lines.append("\nAnd confirm your understanding of:")

            if self.note.get('frozenSections'):
                lines.append("  - Frozen sections that CANNOT be modified")

            if any(a.get('severity') == 'critical' for a in self.note.get('assumptions', [])):
                lines.append("  - Critical assumptions that MUST be maintained")

            if self.note.get('constraints'):
                lines.append("  - Active constraints that apply to this file")

            if self.note.get('tradeoffs'):
                lines.append("  - Known tradeoffs and intentional shortcuts")

        lines.append("\n" + "=" * 80 + "\n")

        return "\n".join(lines)


def verify_acknowledgment(note: Dict[str, Any], file_path: str,
                         claude_message: Optional[str] = None) -> Tuple[bool, str]:
    """
    Convenience function to verify acknowledgment.

    Args:
        note: The design note dictionary
        file_path: The file being modified
        claude_message: Claude's message (if available)

    Returns:
        (is_acknowledged, message) tuple
    """
    verifier = AcknowledgmentVerifier(note, file_path)
    return verifier.verify(claude_message)


def format_acknowledgment_requirement(note: Dict[str, Any], file_path: str) -> str:
    """
    Convenience function to format acknowledgment requirement.

    Args:
        note: The design note dictionary
        file_path: The file being modified

    Returns:
        Formatted acknowledgment requirement string
    """
    verifier = AcknowledgmentVerifier(note, file_path)
    return verifier.format_acknowledgment_requirement()
