"""
Conflict detection for Design Intent Layer plugin.
Detects violations of frozen sections, assumptions, and breaking changes.
"""

import re
from typing import Dict, Any, List, Optional, Tuple


class FrozenViolation:
    """Represents a frozen section violation."""

    def __init__(self, frozen_id: str, reason: str, details: str):
        self.frozen_id = frozen_id
        self.reason = reason
        self.details = details

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': 'frozen_violation',
            'frozenId': self.frozen_id,
            'reason': self.reason,
            'details': self.details
        }

    def format_error(self) -> str:
        return f"""
FROZEN SECTION VIOLATION

Frozen Section: {self.frozen_id}
Reason: {self.reason}

Details:
{self.details}

Resolution:
- Either request an exception in the design note
- Or modify a different section
- Or use /note edit to update the frozen section definition
"""


class AssumptionViolation:
    """Represents an assumption violation."""

    def __init__(self, assumption_id: str, assumption_text: str,
                 violation_type: str, severity: str, details: str):
        self.assumption_id = assumption_id
        self.assumption_text = assumption_text
        self.violation_type = violation_type
        self.severity = severity
        self.details = details

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': 'assumption_violation',
            'assumptionId': self.assumption_id,
            'assumptionText': self.assumption_text,
            'violationType': self.violation_type,
            'severity': self.severity,
            'details': self.details
        }

    def format_warning(self) -> str:
        return f"""
ASSUMPTION VIOLATION DETECTED

Assumption: {self.assumption_id}
"{self.assumption_text}"

Violation Type: {self.violation_type}
Severity: {self.severity}

Details:
{self.details}

Please confirm this change does not violate the documented assumption.
"""


class ConflictDetector:
    """Detects conflicts with design constraints."""

    def __init__(self, note: Dict[str, Any], file_path: str):
        """
        Initialize conflict detector.

        Args:
            note: The design note dictionary
            file_path: The file being modified
        """
        self.note = note
        self.file_path = file_path

    def detect_frozen_violations(self, new_content: str,
                                old_content: Optional[str] = None) -> Optional[FrozenViolation]:
        """
        Detect violations of frozen sections.

        Args:
            new_content: The new content being written
            old_content: The old content (if available for Edit operations)

        Returns:
            FrozenViolation if detected, None otherwise
        """
        frozen_sections = self.note.get('frozenSections', [])

        for frozen in frozen_sections:
            frozen_id = frozen['id']
            reason = frozen['reason']
            exceptions = frozen.get('exceptions', '')

            # Pattern-based frozen section
            if 'pattern' in frozen:
                pattern = frozen['pattern']

                # Check if pattern exists in new content
                if re.search(pattern, new_content, re.IGNORECASE | re.MULTILINE):
                    # If old content available, check if pattern was modified
                    if old_content:
                        old_match = re.search(pattern, old_content, re.IGNORECASE | re.MULTILINE)
                        new_match = re.search(pattern, new_content, re.IGNORECASE | re.MULTILINE)

                        if old_match and new_match:
                            old_text = old_match.group(0)
                            new_text = new_match.group(0)

                            # If pattern content changed, it's a violation
                            if old_text != new_text:
                                # Check for exceptions
                                if self._check_frozen_exception(old_text, new_text, exceptions):
                                    continue

                                return FrozenViolation(
                                    frozen_id=frozen_id,
                                    reason=reason,
                                    details=f"Pattern '{pattern}' was modified.\n\nOld:\n{old_text}\n\nNew:\n{new_text}"
                                )
                    else:
                        # For Write operations (no old content), just warn if pattern is being set
                        # This is less strict but prevents false positives on new files
                        pass

            # Line-range based frozen section
            elif 'lineRange' in frozen:
                # Line range detection requires line-by-line analysis
                # For now, we'll implement a simpler version that checks if specific lines exist
                start_line, end_line = frozen['lineRange']

                # Note: Full line-range detection would require access to the Edit tool's
                # line range parameters, which we'd get from the tool_input
                # For now, we'll skip this and rely on pattern-based detection

        return None

    def _check_frozen_exception(self, old_text: str, new_text: str, exceptions: str) -> bool:
        """
        Check if a change falls under allowed exceptions.

        Args:
            old_text: Old pattern text
            new_text: New pattern text
            exceptions: Exception description

        Returns:
            True if change is allowed by exception, False otherwise
        """
        if not exceptions:
            return False

        exceptions_lower = exceptions.lower()

        # Check for "optional properties with defaults" exception
        if 'optional' in exceptions_lower and 'default' in exceptions_lower:
            # Check if only adding optional properties (very basic heuristic)
            # Look for "?" in TypeScript interfaces
            if '?' in new_text and '?' not in old_text:
                return True

        return False

    def detect_assumption_violations(self, new_content: str) -> List[AssumptionViolation]:
        """
        Detect violations of documented assumptions (heuristic-based).

        Args:
            new_content: The new content being written

        Returns:
            List of assumption violations
        """
        violations = []
        assumptions = self.note.get('assumptions', [])

        for assumption in assumptions:
            assumption_id = assumption['id']
            assumption_text = assumption['text'].lower()
            severity = assumption.get('severity', 'medium')

            # Heuristic 1: Async/await assumptions
            if 'async' in assumption_text and 'await' in assumption_text:
                # Check if code uses setTimeout with 0 (sync alternative)
                if re.search(r'setTimeout.*\(.*\,\s*0\s*\)', new_content):
                    violations.append(AssumptionViolation(
                        assumption_id=assumption_id,
                        assumption_text=assumption['text'],
                        violation_type='sync_instead_of_async',
                        severity=severity,
                        details='Code uses setTimeout with 0ms delay, which is a synchronous pattern, but assumption states async operations are required.'
                    ))

            # Heuristic 2: Dependency assumptions
            if any(keyword in assumption_text for keyword in ['import', 'dependency', 'library', 'package']):
                # Extract potential library names from assumption text
                # Look for capitalized words or quoted strings
                lib_names = re.findall(r'\b[A-Z][a-zA-Z0-9_]+\b', assumption['text'])
                lib_names += re.findall(r'["\']([^"\']+)["\']', assumption['text'])

                for lib_name in lib_names:
                    # Check if import statement exists for this library
                    if not re.search(rf'\bimport\b.*\b{lib_name}\b', new_content, re.IGNORECASE):
                        violations.append(AssumptionViolation(
                            assumption_id=assumption_id,
                            assumption_text=assumption['text'],
                            violation_type='missing_required_dependency',
                            severity=severity,
                            details=f'No import found for {lib_name}, but assumption indicates it is required.'
                        ))

            # Heuristic 3: Threading/concurrency assumptions
            if any(keyword in assumption_text for keyword in ['single-thread', 'single thread', 'not thread-safe']):
                # Check for async/await or threading imports
                if re.search(r'\basync\b|\bawait\b|threading|multiprocessing', new_content):
                    violations.append(AssumptionViolation(
                        assumption_id=assumption_id,
                        assumption_text=assumption['text'],
                        violation_type='concurrency_in_single_threaded',
                        severity=severity,
                        details='Code introduces async or threading constructs, but assumption states single-threaded operation.'
                    ))

        return violations

    def detect_breaking_changes(self, new_content: str,
                                old_content: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Detect breaking API changes (basic implementation).

        Args:
            new_content: The new content
            old_content: The old content (if available)

        Returns:
            List of breaking changes
        """
        breaking_changes = []

        if not old_content:
            return breaking_changes

        # Check for removed public interfaces (TypeScript/JavaScript)
        old_interfaces = self._extract_interfaces(old_content)
        new_interfaces = self._extract_interfaces(new_content)

        for interface_name, old_def in old_interfaces.items():
            if interface_name not in new_interfaces:
                breaking_changes.append({
                    'type': 'removed_interface',
                    'interface': interface_name,
                    'details': f'Public interface {interface_name} was removed'
                })
            else:
                # Check for removed properties
                new_def = new_interfaces[interface_name]
                removed_props = old_def - new_def

                if removed_props:
                    breaking_changes.append({
                        'type': 'removed_properties',
                        'interface': interface_name,
                        'properties': list(removed_props),
                        'details': f'Properties removed from {interface_name}: {", ".join(removed_props)}'
                    })

        return breaking_changes

    def _extract_interfaces(self, content: str) -> Dict[str, set]:
        """
        Extract interface definitions and their properties (basic version).

        Args:
            content: The file content

        Returns:
            Dictionary mapping interface names to sets of property names
        """
        interfaces = {}

        # Match TypeScript/JavaScript interfaces
        # Pattern: export interface Name { ... }
        interface_pattern = r'export\s+interface\s+(\w+)\s*\{([^}]+)\}'

        for match in re.finditer(interface_pattern, content, re.MULTILINE):
            interface_name = match.group(1)
            interface_body = match.group(2)

            # Extract property names
            # Pattern: propertyName: type or propertyName?: type
            prop_pattern = r'(\w+)\s*\??:'
            properties = set(re.findall(prop_pattern, interface_body))

            interfaces[interface_name] = properties

        return interfaces


def detect_conflicts(note: Dict[str, Any], file_path: str,
                    new_content: str, old_content: Optional[str] = None) -> Tuple[
                        Optional[FrozenViolation],
                        List[AssumptionViolation],
                        List[Dict[str, Any]]
                    ]:
    """
    Convenience function to detect all conflicts.

    Args:
        note: The design note dictionary
        file_path: The file being modified
        new_content: The new content
        old_content: The old content (if available)

    Returns:
        (frozen_violation, assumption_violations, breaking_changes) tuple
    """
    detector = ConflictDetector(note, file_path)

    frozen_violation = detector.detect_frozen_violations(new_content, old_content)
    assumption_violations = detector.detect_assumption_violations(new_content)
    breaking_changes = detector.detect_breaking_changes(new_content, old_content)

    return frozen_violation, assumption_violations, breaking_changes
