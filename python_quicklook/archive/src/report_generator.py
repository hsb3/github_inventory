"""
Report generator for Python Quick Look tool.
Handles markdown formatting and output generation.
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    try:
        from .python_quicklook import ClassInfo, FunctionInfo, ModuleInfo, PythonQuickLook
        from .project_context import ProjectContext
        from .diagram_generator import DiagramGenerator, DiagramConfig
        from .asset_manager import AssetManager, AssetManagerConfig
        from .dependency_analyzer import DependencyAnalysisResult
        from .cli_analyzer import CLIAnalysisResult
    except ImportError:
        from python_quicklook import ClassInfo, FunctionInfo, ModuleInfo, PythonQuickLook
        from project_context import ProjectContext
        from diagram_generator import DiagramGenerator, DiagramConfig
        from asset_manager import AssetManager, AssetManagerConfig
        from dependency_analyzer import DependencyAnalysisResult
        from cli_analyzer import CLIAnalysisResult

logger = logging.getLogger(__name__)


class DocstringFormat(Enum):
    """Supported docstring formats."""
    GOOGLE = "google"
    NUMPY = "numpy"
    SPHINX = "sphinx"
    PLAIN = "plain"


class DocstringDisplayMode(Enum):
    """Display modes for docstrings based on length and content."""
    INLINE = "inline"  # Single line, italicized
    BLOCKQUOTE = "blockquote"  # Multi-line, blockquote format
    COLLAPSIBLE = "collapsible"  # Long docstrings, collapsible section
    STRUCTURED = "structured"  # Parsed structured format


@dataclass
class DocstringConfig:
    """Configuration for docstring formatting."""
    # Length thresholds
    inline_max_length: int = 80
    blockquote_max_length: int = 300
    collapsible_threshold: int = 500

    # Display preferences
    preserve_formatting: bool = True
    show_parameter_details: bool = True
    show_return_details: bool = True
    show_examples: bool = True

    # Backwards compatibility
    truncate_mode: bool = False
    truncate_length: int = 100

    # Structured parsing
    parse_structured: bool = True
    preferred_format: Optional[DocstringFormat] = None


@dataclass
class ParsedDocstring:
    """Structured representation of a parsed docstring."""
    summary: str
    description: Optional[str] = None
    parameters: Optional[List[Tuple[str, str, Optional[str]]]] = None  # name, type, description
    returns: Optional[Tuple[Optional[str], str]] = None  # type, description
    raises: Optional[List[Tuple[str, str]]] = None  # exception, description
    examples: Optional[List[str]] = None
    notes: Optional[List[str]] = None
    format_detected: DocstringFormat = DocstringFormat.PLAIN
    raw_content: str = ""


class MarkdownReportGenerator:
    """Generates markdown reports from analyzed Python project data."""

    def __init__(self, analyzer: "PythonQuickLook", output_dir: Optional[Path] = None,
                 enable_diagrams: bool = True, docstring_config: Optional[DocstringConfig] = None):
        self.analyzer = analyzer
        self.stats = analyzer.get_statistics()
        self.context = analyzer.project_context
        self.dependency_analysis = analyzer.dependency_analysis
        self.cli_analysis = analyzer.cli_analysis
        self.output_dir = Path(output_dir or ".")
        self.enable_diagrams = enable_diagrams
        self.docstring_config = docstring_config or DocstringConfig()

        # Initialize asset manager
        try:
            from .asset_manager import AssetManager, AssetManagerConfig
        except ImportError:
            from asset_manager import AssetManager, AssetManagerConfig

        self.asset_manager = AssetManager(
            self.output_dir,
            AssetManagerConfig(clean_on_start=False)
        )

        # Initialize diagram generator if enabled
        self.diagram_generator = None
        if self.enable_diagrams:
            try:
                from .diagram_generator import DiagramGenerator, DiagramConfig
            except ImportError:
                from diagram_generator import DiagramGenerator, DiagramConfig

            self.diagram_generator = DiagramGenerator(
                self.analyzer.target_dir,
                DiagramConfig(output_dir=self.asset_manager.asset_dir)
            )

    def detect_docstring_format(self, docstring: str) -> DocstringFormat:
        """Detect the format of a docstring."""
        if not docstring:
            return DocstringFormat.PLAIN

        # Google style indicators
        google_patterns = [r"Args:", r"Arguments:", r"Parameters:", r"Returns:", r"Yields:", r"Raises:", r"Note:", r"Example:"]
        google_matches = sum(1 for pattern in google_patterns if re.search(pattern, docstring, re.IGNORECASE))

        # NumPy style indicators
        numpy_patterns = [r"Parameters\s*\n\s*-+", r"Returns\s*\n\s*-+", r"Raises\s*\n\s*-+"]
        numpy_matches = sum(1 for pattern in numpy_patterns if re.search(pattern, docstring, re.MULTILINE))

        # Sphinx style indicators
        sphinx_patterns = [r":param\s+\w+:", r":type\s+\w+:", r":returns?:", r":rtype:", r":raises?\s+\w+:"]
        sphinx_matches = sum(1 for pattern in sphinx_patterns if re.search(pattern, docstring))

        # Return the format with the most matches
        if sphinx_matches > max(google_matches, numpy_matches):
            return DocstringFormat.SPHINX
        elif numpy_matches > google_matches:
            return DocstringFormat.NUMPY
        elif google_matches > 0:
            return DocstringFormat.GOOGLE
        else:
            return DocstringFormat.PLAIN

    def parse_google_docstring(self, docstring: str) -> ParsedDocstring:
        """Parse Google-style docstring."""
        try:
            lines = docstring.strip().split('\n')
            parsed = ParsedDocstring(summary="", format_detected=DocstringFormat.GOOGLE, raw_content=docstring)

            current_section = None
            current_content = []

            for line in lines:
                stripped = line.strip()

                # Check for section headers
                if stripped.lower() in ['args:', 'arguments:', 'parameters:']:
                    if current_section == 'summary' and current_content:
                        parsed.summary = ' '.join(current_content).strip()
                    current_section = 'parameters'
                    current_content = []
                    parsed.parameters = []
                elif stripped.lower() == 'returns:':
                    current_section = 'returns'
                    current_content = []
                elif stripped.lower() == 'yields:':
                    current_section = 'yields'
                    current_content = []
                elif stripped.lower() == 'raises:':
                    current_section = 'raises'
                    current_content = []
                    parsed.raises = []
                elif stripped.lower() in ['example:', 'examples:']:
                    current_section = 'examples'
                    current_content = []
                    parsed.examples = []
                elif stripped.lower() in ['note:', 'notes:']:
                    current_section = 'notes'
                    current_content = []
                    parsed.notes = []
                else:
                    if current_section == 'parameters' and stripped and parsed.parameters is not None:
                        # Parse parameter line: "param_name (type): description"
                        param_match = re.match(r'^(\w+)\s*(?:\(([^)]+)\))?\s*:\s*(.*)$', stripped)
                        if param_match:
                            name, param_type, desc = param_match.groups()
                            parsed.parameters.append((name, param_type or "", desc or ""))
                        elif current_content:  # Continue description from previous line
                            if parsed.parameters:
                                name, param_type, desc = parsed.parameters[-1]
                                parsed.parameters[-1] = (name, param_type, f"{desc} {stripped}")
                    elif current_section == 'raises' and stripped and parsed.raises is not None:
                        # Parse raises line: "ExceptionType: description"
                        raise_match = re.match(r'^(\w+)\s*:\s*(.*)$', stripped)
                        if raise_match:
                            exc_type, desc = raise_match.groups()
                            parsed.raises.append((exc_type, desc))
                    elif current_section == 'examples' and parsed.examples is not None:
                        if stripped:
                            parsed.examples.append(stripped)
                    elif current_section == 'notes' and parsed.notes is not None:
                        if stripped:
                            parsed.notes.append(stripped)
                    else:
                        if stripped:
                            current_content.append(stripped)
                        elif current_section is None:
                            current_section = 'summary'

            # Handle remaining content
            if current_section == 'summary' and current_content:
                parsed.summary = ' '.join(current_content).strip()
            elif current_section == 'returns' and current_content:
                content = ' '.join(current_content).strip()
                # Try to parse "type: description" format
                return_match = re.match(r'^([^:]+):\s*(.*)$', content)
                if return_match:
                    parsed.returns = (return_match.group(1).strip(), return_match.group(2).strip())
                else:
                    parsed.returns = (None, content)

            # Extract summary from first sentence if not already set
            if not parsed.summary and lines:
                first_line = lines[0].strip()
                if first_line:
                    parsed.summary = first_line
                    # Look for description in subsequent lines before first section
                    desc_lines = []
                    for line in lines[1:]:
                        stripped = line.strip()
                        if stripped and not any(stripped.lower().startswith(section + ':')
                                              for section in ['args', 'arguments', 'parameters', 'returns', 'yields', 'raises', 'example', 'examples', 'note', 'notes']):
                            desc_lines.append(stripped)
                        else:
                            break
                    if desc_lines:
                        parsed.description = ' '.join(desc_lines).strip()

            return parsed
        except Exception as e:
            logger.warning(f"Failed to parse Google docstring: {e}")
            return ParsedDocstring(summary=docstring.strip().split('\n')[0] if docstring else "", raw_content=docstring)

    def parse_numpy_docstring(self, docstring: str) -> ParsedDocstring:
        """Parse NumPy-style docstring."""
        try:
            parsed = ParsedDocstring(summary="", format_detected=DocstringFormat.NUMPY, raw_content=docstring)

            lines = docstring.strip().split('\n')
            current_section = None
            section_content = []

            for i, line in enumerate(lines):
                stripped = line.strip()

                # Check for NumPy section headers (followed by dashes)
                if i < len(lines) - 1 and re.match(r'^-+$', lines[i + 1].strip()):
                    if current_section == 'summary' and section_content:
                        parsed.summary = ' '.join(section_content).strip()
                    elif current_section == 'description' and section_content:
                        parsed.description = ' '.join(section_content).strip()

                    section_name = stripped.lower()
                    if section_name in ['parameters', 'params']:
                        current_section = 'parameters'
                        parsed.parameters = []
                    elif section_name == 'returns':
                        current_section = 'returns'
                    elif section_name == 'raises':
                        current_section = 'raises'
                        parsed.raises = []
                    elif section_name in ['examples', 'example']:
                        current_section = 'examples'
                        parsed.examples = []
                    elif section_name in ['notes', 'note']:
                        current_section = 'notes'
                        parsed.notes = []
                    else:
                        current_section = section_name

                    section_content = []
                    continue

                # Skip dashes line
                if re.match(r'^-+$', stripped):
                    continue

                if current_section == 'parameters' and stripped and parsed.parameters is not None:
                    # Parse NumPy parameter format: "name : type\n    description"
                    param_match = re.match(r'^(\w+)\s*:\s*(.*)$', stripped)
                    if param_match:
                        name, param_type = param_match.groups()
                        # Look ahead for description
                        desc_lines = []
                        for j in range(i + 1, len(lines)):
                            next_line = lines[j]
                            if next_line.startswith('    ') or next_line.startswith('\t'):
                                desc_lines.append(next_line.strip())
                            elif next_line.strip():
                                break
                        parsed.parameters.append((name, param_type, ' '.join(desc_lines)))
                elif current_section == 'raises' and stripped and parsed.raises is not None:
                    raise_match = re.match(r'^(\w+)\s*(.*)$', stripped)
                    if raise_match:
                        exc_type, desc = raise_match.groups()
                        parsed.raises.append((exc_type, desc))
                elif current_section == 'examples' and parsed.examples is not None:
                    if stripped:
                        parsed.examples.append(stripped)
                elif current_section == 'notes' and parsed.notes is not None:
                    if stripped:
                        parsed.notes.append(stripped)
                elif stripped:
                    section_content.append(stripped)
                elif current_section is None:
                    current_section = 'summary'

            # Handle final section
            if current_section == 'summary' and section_content:
                parsed.summary = ' '.join(section_content).strip()
            elif current_section == 'description' and section_content:
                parsed.description = ' '.join(section_content).strip()
            elif current_section == 'returns' and section_content:
                content = ' '.join(section_content).strip()
                parsed.returns = (None, content)

            return parsed
        except Exception as e:
            logger.warning(f"Failed to parse NumPy docstring: {e}")
            return ParsedDocstring(summary=docstring.strip().split('\n')[0] if docstring else "", raw_content=docstring)

    def parse_sphinx_docstring(self, docstring: str) -> ParsedDocstring:
        """Parse Sphinx-style docstring."""
        try:
            parsed = ParsedDocstring(summary="", format_detected=DocstringFormat.SPHINX, raw_content=docstring)

            lines = docstring.strip().split('\n')
            summary_lines = []
            current_param = None

            parsed.parameters = []
            parsed.raises = []

            for line in lines:
                stripped = line.strip()

                # Parameter definitions
                param_match = re.match(r'^:param\s+(\w+)\s*:\s*(.*)$', stripped)
                if param_match:
                    name, desc = param_match.groups()
                    current_param = (name, "", desc)
                    parsed.parameters.append(current_param)
                    continue

                # Parameter type definitions
                type_match = re.match(r'^:type\s+(\w+)\s*:\s*(.*)$', stripped)
                if type_match:
                    name, param_type = type_match.groups()
                    # Update the parameter with type information
                    for i, (pname, _, pdesc) in enumerate(parsed.parameters):
                        if pname == name:
                            parsed.parameters[i] = (pname, param_type, pdesc)
                            break
                    continue

                # Return descriptions
                return_match = re.match(r'^:returns?\s*:\s*(.*)$', stripped)
                if return_match:
                    parsed.returns = (None, return_match.group(1))
                    continue

                # Return type
                rtype_match = re.match(r'^:rtype\s*:\s*(.*)$', stripped)
                if rtype_match:
                    if parsed.returns:
                        parsed.returns = (rtype_match.group(1), parsed.returns[1])
                    else:
                        parsed.returns = (rtype_match.group(1), "")
                    continue

                # Raises
                raises_match = re.match(r'^:raises?\s+(\w+)\s*:\s*(.*)$', stripped)
                if raises_match:
                    exc_type, desc = raises_match.groups()
                    parsed.raises.append((exc_type, desc))
                    continue

                # Regular content (summary/description)
                if stripped and not re.match(r'^:[a-z]+.*:', stripped):
                    summary_lines.append(stripped)

            if summary_lines:
                # First line/sentence is summary, rest is description
                full_text = ' '.join(summary_lines)
                sentences = re.split(r'(?<=[.!?])\s+', full_text)
                if sentences:
                    parsed.summary = sentences[0]
                    if len(sentences) > 1:
                        parsed.description = ' '.join(sentences[1:])

            return parsed
        except Exception as e:
            logger.warning(f"Failed to parse Sphinx docstring: {e}")
            return ParsedDocstring(summary=docstring.strip().split('\n')[0] if docstring else "", raw_content=docstring)

    def parse_docstring(self, docstring: str) -> ParsedDocstring:
        """Parse a docstring into structured format."""
        try:
            if not docstring or not self.docstring_config.parse_structured:
                return ParsedDocstring(summary=docstring or "", raw_content=docstring or "")

            # Detect format if not specified
            if self.docstring_config.preferred_format:
                format_type = self.docstring_config.preferred_format
            else:
                format_type = self.detect_docstring_format(docstring)

            # Parse based on detected format
            if format_type == DocstringFormat.GOOGLE:
                return self.parse_google_docstring(docstring)
            elif format_type == DocstringFormat.NUMPY:
                return self.parse_numpy_docstring(docstring)
            elif format_type == DocstringFormat.SPHINX:
                return self.parse_sphinx_docstring(docstring)
            else:
                # Plain format - just extract summary and description
                lines = docstring.strip().split('\n')
                if lines:
                    summary = lines[0].strip()
                    description = None
                    if len(lines) > 1:
                        desc_lines = [line.strip() for line in lines[1:] if line.strip()]
                        if desc_lines:
                            description = ' '.join(desc_lines)
                    return ParsedDocstring(
                        summary=summary,
                        description=description,
                        format_detected=DocstringFormat.PLAIN,
                        raw_content=docstring
                    )
                return ParsedDocstring(summary="", raw_content=docstring)
        except Exception as e:
            logger.warning(f"Failed to parse docstring: {e}")
            return ParsedDocstring(summary=docstring.strip().split('\n')[0] if docstring else "", raw_content=docstring or "")

    def determine_display_mode(self, docstring: str, parsed: Optional[ParsedDocstring] = None) -> DocstringDisplayMode:
        """Determine the appropriate display mode for a docstring."""
        if not docstring:
            return DocstringDisplayMode.INLINE

        length = len(docstring)
        line_count = len(docstring.split('\n'))

        # Check if it's structured and should be formatted as such
        if (parsed and parsed.format_detected != DocstringFormat.PLAIN and
            (parsed.parameters or parsed.returns or parsed.raises or parsed.examples)):
            return DocstringDisplayMode.STRUCTURED

        # Very long docstrings should be collapsible
        if length > self.docstring_config.collapsible_threshold:
            return DocstringDisplayMode.COLLAPSIBLE

        # Short single-line docstrings are inline
        if line_count == 1 and length <= self.docstring_config.inline_max_length:
            return DocstringDisplayMode.INLINE

        # Medium-length docstrings use blockquote
        if length <= self.docstring_config.blockquote_max_length:
            return DocstringDisplayMode.BLOCKQUOTE

        # Default to collapsible for longer content
        return DocstringDisplayMode.COLLAPSIBLE

    def format_docstring(self, docstring: str, indent: str = "  ") -> str:
        """Format a docstring for markdown output with intelligent formatting."""
        try:
            if not docstring:
                return f"{indent}*No docstring*"

            # Handle backwards compatibility mode
            if self.docstring_config.truncate_mode:
                return self._format_docstring_legacy(docstring, indent)

            # Parse the docstring
            parsed = self.parse_docstring(docstring)
            display_mode = self.determine_display_mode(docstring, parsed)

            # Format based on display mode
            if display_mode == DocstringDisplayMode.INLINE:
                return self._format_inline(parsed, indent)
            elif display_mode == DocstringDisplayMode.BLOCKQUOTE:
                return self._format_blockquote(parsed, indent)
            elif display_mode == DocstringDisplayMode.COLLAPSIBLE:
                return self._format_collapsible(parsed, indent)
            elif display_mode == DocstringDisplayMode.STRUCTURED:
                return self._format_structured(parsed, indent)
            else:
                return self._format_blockquote(parsed, indent)  # Fallback
        except Exception as e:
            logger.warning(f"Error formatting docstring: {e}")
            # Fallback to simple formatting
            return f"{indent}*{docstring.strip().split(chr(10))[0] if docstring else 'No docstring'}*"

    def _format_docstring_legacy(self, docstring: str, indent: str) -> str:
        """Legacy formatting for backwards compatibility."""
        lines = docstring.strip().split("\n")
        if len(lines) == 1:
            return f"{indent}*{lines[0].strip()}*"

        # Multi-line docstring with truncation
        truncated = docstring[:self.docstring_config.truncate_length]
        if len(docstring) > self.docstring_config.truncate_length:
            truncated += "..."

        formatted_lines = [f"{indent}*{lines[0].strip()}*"]
        if len(lines) > 1:
            formatted_lines.append(f"{indent}...")
        return "\n".join(formatted_lines)

    def _format_inline(self, parsed: ParsedDocstring, indent: str) -> str:
        """Format as inline italic text."""
        return f"{indent}*{parsed.summary}*"

    def _format_blockquote(self, parsed: ParsedDocstring, indent: str) -> str:
        """Format as blockquote for medium-length docstrings."""
        lines = []

        # Add summary
        if parsed.summary:
            lines.append(f"{indent}> {parsed.summary}")

        # Add description if available
        if parsed.description:
            lines.append(f"{indent}> ")
            # Split description into reasonable line lengths
            desc_words = parsed.description.split()
            current_line = []
            for word in desc_words:
                if len(' '.join(current_line + [word])) > 80:
                    if current_line:
                        lines.append(f"{indent}> {' '.join(current_line)}")
                        current_line = [word]
                    else:
                        lines.append(f"{indent}> {word}")
                else:
                    current_line.append(word)
            if current_line:
                lines.append(f"{indent}> {' '.join(current_line)}")

        return "\n".join(lines)

    def _format_collapsible(self, parsed: ParsedDocstring, indent: str) -> str:
        """Format as collapsible section for long docstrings."""
        lines = []

        # Create collapsible section
        summary_text = parsed.summary if parsed.summary else "View docstring"
        lines.append(f"{indent}<details>")
        lines.append(f"{indent}<summary><em>{summary_text}</em></summary>")
        lines.append(f"{indent}")

        # Add full content in code block to preserve formatting
        content_lines = parsed.raw_content.split('\n')
        lines.append(f"{indent}```")
        for line in content_lines:
            lines.append(f"{indent}{line}")
        lines.append(f"{indent}```")

        lines.append(f"{indent}</details>")

        return "\n".join(lines)

    def _format_structured(self, parsed: ParsedDocstring, indent: str) -> str:
        """Format structured docstring with sections."""
        lines = []

        # Summary
        if parsed.summary:
            lines.append(f"{indent}**{parsed.summary}**")
            lines.append(f"{indent}")

        # Description
        if parsed.description:
            lines.append(f"{indent}{parsed.description}")
            lines.append(f"{indent}")

        # Parameters
        if parsed.parameters and self.docstring_config.show_parameter_details:
            lines.append(f"{indent}*Parameters:*")
            for name, param_type, desc in parsed.parameters:
                type_info = f" ({param_type})" if param_type else ""
                lines.append(f"{indent}- `{name}`{type_info}: {desc}")
            lines.append(f"{indent}")

        # Returns
        if parsed.returns and self.docstring_config.show_return_details:
            return_type, return_desc = parsed.returns
            type_info = f" ({return_type})" if return_type else ""
            lines.append(f"{indent}*Returns{type_info}:* {return_desc}")
            lines.append(f"{indent}")

        # Raises
        if parsed.raises:
            lines.append(f"{indent}*Raises:*")
            for exc_type, desc in parsed.raises:
                lines.append(f"{indent}- `{exc_type}`: {desc}")
            lines.append(f"{indent}")

        # Examples
        if parsed.examples and self.docstring_config.show_examples:
            lines.append(f"{indent}*Examples:*")
            lines.append(f"{indent}```python")
            for example in parsed.examples:
                lines.append(f"{indent}{example}")
            lines.append(f"{indent}```")
            lines.append(f"{indent}")

        # Notes
        if parsed.notes:
            lines.append(f"{indent}*Notes:*")
            for note in parsed.notes:
                lines.append(f"{indent}- {note}")
            lines.append(f"{indent}")

        # Remove trailing empty line
        while lines and not lines[-1].strip():
            lines.pop()

        return "\n".join(lines)

    def format_function(self, func: "FunctionInfo", indent: str = "  ") -> str:
        """Format a function for markdown output."""
        output = []

        # Function signature
        prefix = ""
        if func.is_async:
            prefix = "async "
        if func.is_property:
            prefix += "@property "
        elif func.is_staticmethod:
            prefix += "@staticmethod "
        elif func.is_classmethod:
            prefix += "@classmethod "

        output.append(f"{indent}- **{prefix}{func.signature}**")

        # Decorators (if any beyond the common ones)
        other_decorators = [
            d
            for d in func.decorators
            if not any(
                common in d for common in ["property", "staticmethod", "classmethod"]
            )
        ]
        if other_decorators:
            output.append(f"{indent}  - *Decorators: {', '.join(other_decorators)}*")

        # Docstring
        if func.docstring:
            output.append(self.format_docstring(func.docstring, indent + "  "))
        else:
            output.append(f"{indent}  *No docstring*")

        return "\n".join(output)

    def format_class(self, cls: "ClassInfo", indent: str = "") -> str:
        """Format a class for markdown output."""
        output = []

        # Class header
        inheritance = ""
        if cls.bases:
            inheritance = f" (inherits from: {', '.join(cls.bases)})"

        output.append(f"{indent}### Class: {cls.name}{inheritance}")
        output.append("")

        # Decorators
        if cls.decorators:
            output.append(f"{indent}*Decorators: {', '.join(cls.decorators)}*")
            output.append("")

        # Class docstring
        if cls.docstring:
            output.append(self.format_docstring(cls.docstring, indent))
        else:
            output.append(f"{indent}*No docstring*")
        output.append("")

        # Methods
        if cls.methods:
            output.append(f"{indent}**Methods:**")
            output.append("")

            # Group methods by type
            regular_methods = [
                m
                for m in cls.methods
                if not m.is_property and not m.is_staticmethod and not m.is_classmethod
            ]
            properties = [m for m in cls.methods if m.is_property]
            static_methods = [m for m in cls.methods if m.is_staticmethod]
            class_methods = [m for m in cls.methods if m.is_classmethod]

            # Regular methods
            for method in regular_methods:
                output.append(self.format_function(method, indent))
                output.append("")

            # Properties
            if properties:
                output.append(f"{indent}**Properties:**")
                output.append("")
                for prop in properties:
                    output.append(self.format_function(prop, indent))
                    output.append("")

            # Static methods
            if static_methods:
                output.append(f"{indent}**Static Methods:**")
                output.append("")
                for method in static_methods:
                    output.append(self.format_function(method, indent))
                    output.append("")

            # Class methods
            if class_methods:
                output.append(f"{indent}**Class Methods:**")
                output.append("")
                for method in class_methods:
                    output.append(self.format_function(method, indent))
                    output.append("")
        else:
            output.append(f"{indent}*No methods defined*")
            output.append("")

        return "\n".join(output)

    def format_module(self, module: "ModuleInfo") -> str:
        """Format a module for markdown output."""
        output = []

        # Module header
        output.append(f"## Module: {module.name}")
        output.append(f"**File:** `{module.path}`")
        output.append("")

        # Module docstring
        if module.docstring:
            output.append("**Description:**")
            output.append(self.format_docstring(module.docstring, ""))
        else:
            output.append("*No module docstring*")
        output.append("")

        # Key imports (limit to avoid clutter)
        if module.imports:
            key_imports = [imp for imp in module.imports[:10]]  # Show first 10
            output.append("**Key Imports:**")
            for imp in key_imports:
                output.append(f"- `{imp}`")
            if len(module.imports) > 10:
                output.append(f"- *... and {len(module.imports) - 10} more*")
            output.append("")

        # Classes
        if module.classes:
            for cls in module.classes:
                output.append(self.format_class(cls))

        # Functions
        if module.functions:
            output.append("### Functions")
            output.append("")
            for func in module.functions:
                output.append(self.format_function(func))
                output.append("")

        # If no classes or functions
        if not module.classes and not module.functions:
            output.append("*No classes or functions defined in this module*")
            output.append("")

        output.append("---")
        output.append("")

        return "\n".join(output)

    def generate_visual_overview(self) -> str:
        """Generate visual overview section with diagrams."""
        if not self.enable_diagrams or not self.diagram_generator:
            return ""

        output = []
        output.append("## 📊 Visual Project Overview")
        output.append("")

        try:
            # Generate diagrams
            result = self.diagram_generator.generate_diagrams(self.dependency_analysis)

            if result.success:
                # Class diagram
                if result.class_diagram_path:
                    # Copy/register the diagram with asset manager
                    asset_info = self.asset_manager.register_asset(
                        result.class_diagram_path, "diagram", created=True
                    )
                    if asset_info:
                        output.append("### Class Diagram")
                        output.append("")
                        output.append("This diagram shows the class relationships and structure of the project:")
                        output.append("")
                        output.append(self.asset_manager.get_markdown_image_ref(
                            asset_info.path.name, "Class Diagram"
                        ))
                        output.append("")

                # Package diagram
                if result.package_diagram_path:
                    # Copy/register the diagram with asset manager
                    asset_info = self.asset_manager.register_asset(
                        result.package_diagram_path, "diagram", created=True
                    )
                    if asset_info:
                        output.append("### Package Diagram")
                        output.append("")
                        output.append("This diagram shows the package structure and dependencies:")
                        output.append("")
                        output.append(self.asset_manager.get_markdown_image_ref(
                            asset_info.path.name, "Package Diagram"
                        ))
                        output.append("")

                # Dependency diagram
                if result.dependency_diagram_path:
                    # Copy/register the diagram with asset manager
                    asset_info = self.asset_manager.register_asset(
                        result.dependency_diagram_path, "diagram", created=True
                    )
                    if asset_info:
                        output.append("### Dependency Diagram")
                        output.append("")
                        output.append("This diagram shows the module dependency relationships:")
                        output.append("")
                        output.append(self.asset_manager.get_markdown_image_ref(
                            asset_info.path.name, "Dependency Diagram"
                        ))
                        output.append("")

                # If we have diagrams, add some explanatory text
                if result.class_diagram_path or result.package_diagram_path or result.dependency_diagram_path:
                    output.append("**Diagram Legend:**")
                    if result.class_diagram_path:
                        output.append("- **Class Diagram:** Classes shown as boxes with methods and attributes")
                        output.append("- Inheritance relationships shown with arrows")
                    if result.package_diagram_path:
                        output.append("- **Package Diagram:** Package structure and relationships")
                    if result.dependency_diagram_path:
                        output.append("- **Dependency Diagram:** Module dependency relationships")
                        output.append("- Blue arrows: Internal dependencies")
                        output.append("- Red dashed arrows: External dependencies")
                        output.append("- Colors indicate dependency depth (blue=leaf, green=low, yellow=high)")
                        output.append("- Red thick arrows: Circular dependencies (should be avoided)")
                    output.append("")

            else:
                # Diagram generation failed, show fallback content
                try:
                    from .diagram_generator import create_fallback_diagram_content
                except ImportError:
                    from diagram_generator import create_fallback_diagram_content

                fallback_content = create_fallback_diagram_content(
                    self.analyzer.target_dir.name or "Python Project"
                )
                output.append(fallback_content)

                # Log the failure
                logger.warning(f"Diagram generation failed: {result.error_message}")

                # Show installation instructions if available
                if result.error_message and "dependencies" in result.error_message.lower():
                    instructions = self.diagram_generator.get_installation_instructions()
                    if instructions:
                        output.append("**Installation Instructions:**")
                        output.append("")
                        for dep, instruction in instructions.items():
                            output.append(f"**{dep}:**")
                            for line in instruction.split('\n'):
                                output.append(f"  {line}")
                            output.append("")

            # Show any warnings
            if result.warnings:
                output.append("**⚠️ Warnings:**")
                for warning in result.warnings:
                    output.append(f"- {warning}")
                output.append("")

        except Exception as e:
            logger.error(f"Error generating visual overview: {e}")
            # Return fallback content
            try:
                from .diagram_generator import create_fallback_diagram_content
            except ImportError:
                from diagram_generator import create_fallback_diagram_content

            fallback_content = create_fallback_diagram_content(
                self.analyzer.target_dir.name or "Python Project"
            )
            output.append(fallback_content)

        output.append("---")
        output.append("")
        return "\n".join(output)

    def generate_project_overview(self) -> str:
        """Generate project overview section from context."""
        if not self.context:
            return ""

        output = []
        output.append("## 🏗️ Project Overview")
        output.append("")

        # Project name and description
        if self.context.metadata:
            if self.context.metadata.name:
                output.append(f"**Name:** {self.context.metadata.name}")
            if self.context.metadata.version:
                output.append(f"**Version:** {self.context.metadata.version}")
            if self.context.metadata.description:
                output.append(f"**Description:** {self.context.metadata.description}")
            if self.context.metadata.author:
                output.append(f"**Author:** {self.context.metadata.author}")
            if self.context.metadata.license:
                output.append(f"**License:** {self.context.metadata.license}")
            if self.context.metadata.homepage:
                output.append(f"**Homepage:** [{self.context.metadata.homepage}]({self.context.metadata.homepage})")
            if self.context.metadata.repository:
                output.append(f"**Repository:** [{self.context.metadata.repository}]({self.context.metadata.repository})")
            output.append("")

        # Project structure
        if self.context.structure:
            output.append("### Project Structure")
            output.append("")

            if self.context.structure.is_package:
                output.append("- ✅ **Package structure detected**")
            else:
                output.append("- ❌ **No package structure detected**")

            if self.context.structure.has_src_layout:
                output.append("- 📁 **Uses src layout**")

            if self.context.structure.package_dirs:
                output.append(f"- 📦 **Package directories:** {', '.join(self.context.structure.package_dirs)}")

            if self.context.structure.test_dirs:
                output.append(f"- 🧪 **Test directories:** {', '.join(self.context.structure.test_dirs)}")

            if self.context.structure.doc_dirs:
                output.append(f"- 📚 **Documentation directories:** {', '.join(self.context.structure.doc_dirs)}")

            # Build and deployment
            build_tools = []
            if self.context.structure.has_dockerfile:
                build_tools.append("Docker")
            if self.context.structure.has_docker_compose:
                build_tools.append("Docker Compose")
            if self.context.structure.has_makefile:
                build_tools.append("Make")

            if build_tools:
                output.append(f"- 🔧 **Build tools:** {', '.join(build_tools)}")

            # Dependency management
            dep_tools = []
            if self.context.structure.has_requirements_txt:
                dep_tools.append("requirements.txt")
            if self.context.structure.has_poetry_lock:
                dep_tools.append("Poetry")
            if self.context.structure.has_pipfile:
                dep_tools.append("Pipenv")

            if dep_tools:
                output.append(f"- 📋 **Dependency management:** {', '.join(dep_tools)}")

            output.append("")

        # Detected frameworks
        if self.context.detected_frameworks:
            output.append("### Detected Frameworks")
            output.append("")
            for framework in sorted(self.context.detected_frameworks):
                output.append(f"- {framework}")
            output.append("")

        # Detected patterns
        if self.context.detected_patterns:
            output.append("### Development Patterns")
            output.append("")
            for pattern in sorted(self.context.detected_patterns):
                output.append(f"- {pattern}")
            output.append("")

        # Entry points
        if self.context.metadata and self.context.metadata.entry_points:
            output.append("### Entry Points")
            output.append("")
            for entry_point in self.context.metadata.entry_points:
                output.append(f"- **{entry_point.name}** ({entry_point.entry_type})")
                output.append(f"  - *Module:* `{entry_point.module_path}:{entry_point.function_name}`")
                if entry_point.description:
                    output.append(f"  - *Description:* {entry_point.description}")
            output.append("")

        # CLI commands
        if self.context.cli_commands:
            output.append("### CLI Commands")
            output.append("")
            for command in self.context.cli_commands:
                output.append(f"- **{command.name}**")
                output.append(f"  - *Module:* `{command.module_path}:{command.function_name}`")
                if command.description:
                    output.append(f"  - *Description:* {command.description}")
            output.append("")

        # README information
        if self.context.readme_info:
            readme = self.context.readme_info
            output.append("### README Information")
            output.append("")
            output.append(f"- **File:** `{readme.file_path}`")
            if readme.title:
                output.append(f"- **Title:** {readme.title}")
            if readme.description:
                output.append(f"- **Description:** {readme.description}")
            if readme.badges:
                output.append(f"- **Badges:** {len(readme.badges)} found")
            if readme.links:
                output.append(f"- **Links:** {len(readme.links)} found")
            if readme.has_toc:
                output.append("- **Table of Contents:** Yes")
            if readme.sections:
                output.append(f"- **Sections:** {len(readme.sections)} ({', '.join(readme.sections[:5])}{'...' if len(readme.sections) > 5 else ''})")
            output.append("")

        # Dependencies
        if self.context.metadata and self.context.metadata.dependencies:
            output.append("### Dependencies")
            output.append("")

            # Main dependencies
            main_deps = [dep for dep in self.context.metadata.dependencies if dep.group == "main"]
            if main_deps:
                output.append("**Main dependencies:**")
                for dep in main_deps[:10]:  # Show first 10
                    version_info = f" ({dep.version_spec})" if dep.version_spec else ""
                    output.append(f"- `{dep.name}{version_info}`")
                if len(main_deps) > 10:
                    output.append(f"- *... and {len(main_deps) - 10} more*")
                output.append("")

            # Optional dependencies
            if self.context.metadata.optional_dependencies:
                for group, deps in self.context.metadata.optional_dependencies.items():
                    output.append(f"**{group.title()} dependencies:**")
                    for dep in deps[:5]:  # Show first 5 per group
                        version_info = f" ({dep.version_spec})" if dep.version_spec else ""
                        output.append(f"- `{dep.name}{version_info}`")
                    if len(deps) > 5:
                        output.append(f"- *... and {len(deps) - 5} more*")
                    output.append("")

        output.append("---")
        output.append("")

        return "\n".join(output)

    def generate_dependency_overview(self) -> str:
        """Generate dependency analysis overview section."""
        if not self.dependency_analysis:
            return ""

        output = []
        output.append("## 🔗 Dependency Analysis")
        output.append("")

        stats = self.dependency_analysis.statistics
        graph = self.dependency_analysis.dependency_graph

        # Summary statistics
        output.append("### Dependency Statistics")
        output.append("")
        output.append(f"- **Total Dependencies:** {stats['total_dependencies']}")
        output.append(f"- **Internal Dependencies:** {stats['internal_dependencies']}")
        output.append(f"- **External Dependencies:** {stats['external_dependencies']}")
        output.append(f"- **Standard Library Dependencies:** {stats['stdlib_dependencies']}")
        output.append("")

        if stats['unique_external_modules'] > 0:
            output.append(f"- **Unique External Packages:** {stats['unique_external_modules']}")
        if stats['max_dependency_depth'] > 0:
            output.append(f"- **Maximum Dependency Depth:** {stats['max_dependency_depth']}")
            output.append(f"- **Average Dependency Depth:** {stats['avg_dependency_depth']:.1f}")

        if stats.get('max_fan_out', 0) > 0:
            output.append(f"- **Maximum Fan-out:** {stats['max_fan_out']} (dependencies from one module)")
            output.append(f"- **Average Fan-out:** {stats['avg_fan_out']:.1f}")

        if stats.get('max_fan_in', 0) > 0:
            output.append(f"- **Maximum Fan-in:** {stats['max_fan_in']} (modules depending on one module)")
            output.append(f"- **Average Fan-in:** {stats['avg_fan_in']:.1f}")

        output.append("")

        # Circular dependencies warning
        if graph.circular_dependencies:
            output.append("### ⚠️ Circular Dependencies Detected")
            output.append("")
            output.append(f"Found {len(graph.circular_dependencies)} circular dependency chain(s):")
            output.append("")
            for i, cycle in enumerate(graph.circular_dependencies, 1):
                cycle_str = " → ".join(cycle)
                output.append(f"{i}. `{cycle_str}`")
            output.append("")
            output.append("**Recommendation:** Consider refactoring to break these circular dependencies.")
            output.append("")

        # Top external dependencies
        if graph.all_external_modules:
            output.append("### Most Common External Dependencies")
            output.append("")

            # Count usage of each external module
            external_usage = {}
            for deps in graph.external_dependencies.values():
                for dep in deps:
                    external_usage[dep] = external_usage.get(dep, 0) + 1

            # Show top 10
            sorted_external = sorted(external_usage.items(), key=lambda x: x[1], reverse=True)
            for dep, count in sorted_external[:10]:
                output.append(f"- **{dep}** (used by {count} module{'s' if count != 1 else ''})")

            if len(sorted_external) > 10:
                output.append(f"- *...and {len(sorted_external) - 10} more*")
            output.append("")

        # Internal dependency structure
        if graph.internal_dependencies:
            output.append("### Internal Module Dependencies")
            output.append("")

            # Show modules with highest fan-out (most dependencies)
            modules_by_deps = [(module, len(deps)) for module, deps in graph.internal_dependencies.items()]
            modules_by_deps.sort(key=lambda x: x[1], reverse=True)

            if modules_by_deps:
                output.append("**Modules with most dependencies:**")
                for module, dep_count in modules_by_deps[:5]:
                    deps = graph.internal_dependencies[module]
                    output.append(f"- **{module}** → {dep_count} dependencies")
                    for dep in deps[:3]:  # Show first 3 dependencies
                        output.append(f"  - `{dep}`")
                    if len(deps) > 3:
                        output.append(f"  - *...and {len(deps) - 3} more*")
                output.append("")

            # Show most depended-upon modules (highest fan-in)
            fan_in_count = {}
            for deps in graph.internal_dependencies.values():
                for dep in deps:
                    fan_in_count[dep] = fan_in_count.get(dep, 0) + 1

            if fan_in_count:
                sorted_fan_in = sorted(fan_in_count.items(), key=lambda x: x[1], reverse=True)
                output.append("**Most depended-upon modules:**")
                for module, count in sorted_fan_in[:5]:
                    output.append(f"- **{module}** (imported by {count} module{'s' if count != 1 else ''})")
                output.append("")

        # Show any errors or warnings
        if self.dependency_analysis.errors:
            output.append("### ⚠️ Dependency Analysis Errors")
            output.append("")
            for error in self.dependency_analysis.errors:
                output.append(f"- {error}")
            output.append("")

        if self.dependency_analysis.warnings:
            output.append("### ⚠️ Dependency Analysis Warnings")
            output.append("")
            for warning in self.dependency_analysis.warnings:
                output.append(f"- {warning}")
            output.append("")

        output.append("---")
        output.append("")

        return "\n".join(output)

    def generate_configuration_overview(self) -> str:
        """Generate configuration analysis overview section."""
        if not hasattr(self.analyzer, 'configuration_analysis') or not self.analyzer.configuration_analysis:
            return ""

        config = self.analyzer.configuration_analysis
        output = []
        output.append("## ⚙️ Project Configuration")
        output.append("")

        # Build system information
        if config.build_system:
            output.append("### Build System")
            output.append("")
            output.append(f"- **Build Backend:** `{config.build_system.build_backend or 'Not specified'}`")
            output.append(f"- **Build System:** {config.build_system.system.title()}")

            if config.build_system.requires:
                output.append("- **Build Requirements:**")
                for req in config.build_system.requires:
                    output.append(f"  - `{req}`")

            # System-specific configuration details
            if config.build_system.system == "poetry" and config.build_system.poetry_config:
                poetry_config = config.build_system.poetry_config
                if "build" in poetry_config:
                    output.append("- **Poetry Build Configuration:** Custom build script detected")
                if "source" in poetry_config:
                    output.append(f"- **Poetry Sources:** {len(poetry_config['source'])} configured")

            elif config.build_system.system == "hatch" and config.build_system.hatch_config:
                hatch_config = config.build_system.hatch_config
                if "envs" in hatch_config:
                    output.append(f"- **Hatch Environments:** {len(hatch_config['envs'])} configured")

            output.append("")

        # Configuration files found
        if config.config_files:
            output.append("### Configuration Files")
            output.append("")
            output.append("The following configuration files were detected:")
            output.append("")
            for config_file in sorted(config.config_files):
                output.append(f"- `{config_file}`")
            output.append("")

        # Tool configurations
        if config.tool_configs:
            output.append("### Development Tools Configuration")
            output.append("")

            # Group tools by category
            formatters = {}
            linters = {}
            testing = {}
            other_tools = {}

            for tool_name, tool_config in config.tool_configs.items():
                if tool_name in ["black", "autopep8", "yapf", "isort"]:
                    formatters[tool_name] = tool_config
                elif tool_name in ["ruff", "flake8", "pylint", "mypy", "pyflakes", "bandit"]:
                    linters[tool_name] = tool_config
                elif tool_name in ["pytest", "coverage", "tox", "nox"]:
                    testing[tool_name] = tool_config
                else:
                    other_tools[tool_name] = tool_config

            # Format each category
            if formatters:
                output.append("#### Code Formatters")
                output.append("")
                for tool_name, tool_config in formatters.items():
                    output.append(self._format_tool_config(tool_name, tool_config))
                output.append("")

            if linters:
                output.append("#### Linters & Type Checkers")
                output.append("")
                for tool_name, tool_config in linters.items():
                    output.append(self._format_tool_config(tool_name, tool_config))
                output.append("")

            if testing:
                output.append("#### Testing Tools")
                output.append("")
                for tool_name, tool_config in testing.items():
                    output.append(self._format_tool_config(tool_name, tool_config))
                output.append("")

            if other_tools:
                output.append("#### Other Tools")
                output.append("")
                for tool_name, tool_config in other_tools.items():
                    output.append(self._format_tool_config(tool_name, tool_config))
                output.append("")

        # Dependencies overview
        if config.dependencies:
            output.append("### Dependency Overview")
            output.append("")

            total_deps = sum(len(deps) for deps in config.dependencies.values())
            output.append(f"**Total Dependencies:** {total_deps} across {len(config.dependencies)} categories")
            output.append("")

            for category, deps in config.dependencies.items():
                if not deps:
                    continue

                output.append(f"#### {category.title()} Dependencies ({len(deps)})")
                output.append("")

                # Show first 10 dependencies with details
                for dep in deps[:10]:
                    dep_line = f"- **`{dep.name}`**"

                    details = []
                    if dep.version_spec:
                        details.append(f"version: `{dep.version_spec}`")
                    if dep.extras:
                        details.append(f"extras: `{', '.join(dep.extras)}`")
                    if dep.markers:
                        details.append(f"markers: `{dep.markers}`")
                    if dep.editable:
                        details.append("editable: yes")
                    if dep.url:
                        details.append(f"source: `{dep.url[:50]}{'...' if len(dep.url) > 50 else ''}`")

                    if details:
                        dep_line += f" - {'; '.join(details)}"

                    output.append(dep_line)

                if len(deps) > 10:
                    output.append(f"- *... and {len(deps) - 10} more dependencies*")
                output.append("")

        # Requirements files
        if config.requirements_files:
            output.append("### Requirements Files")
            output.append("")

            for req_file in config.requirements_files:
                output.append(f"#### `{req_file.file_path}`")

                if req_file.dependencies:
                    output.append(f"- **Dependencies:** {len(req_file.dependencies)}")

                if req_file.includes:
                    output.append("- **Includes:** ")
                    for include in req_file.includes:
                        output.append(f"  - `{include}`")

                if req_file.options:
                    output.append("- **Pip Options:**")
                    for option, value in req_file.options.items():
                        output.append(f"  - `{option}`: `{value}`")

                output.append("")

        # Python version requirements
        if config.python_versions:
            output.append("### Python Version Requirements")
            output.append("")
            for version in sorted(config.python_versions):
                output.append(f"- `{version}`")
            output.append("")

        # Environment variables
        if config.environment_variables:
            output.append("### Environment Variables")
            output.append("")
            output.append(f"The following {len(config.environment_variables)} environment variables were detected:")
            output.append("")

            # Sort environment variables for consistent output
            sorted_env_vars = sorted(config.environment_variables)
            for env_var in sorted_env_vars[:20]:  # Show first 20
                output.append(f"- `{env_var}`")

            if len(sorted_env_vars) > 20:
                output.append(f"- *... and {len(sorted_env_vars) - 20} more*")
            output.append("")

        # Show any errors or warnings
        if config.errors:
            output.append("### ⚠️ Configuration Analysis Errors")
            output.append("")
            for error in config.errors:
                output.append(f"- {error}")
            output.append("")

        if config.warnings:
            output.append("### ⚠️ Configuration Analysis Warnings")
            output.append("")
            for warning in config.warnings:
                output.append(f"- {warning}")
            output.append("")

        output.append("---")
        output.append("")

        return "\n".join(output)

    def _format_tool_config(self, tool_name: str, tool_config) -> str:
        """Format a tool configuration for markdown output."""
        try:
            from .configuration_analyzer import ToolConfig
        except ImportError:
            from configuration_analyzer import ToolConfig

        lines = []

        # Tool header
        lines.append(f"**{tool_name.title()}** *(configured in {tool_config.config_source})*")

        # Common settings
        settings = []
        if tool_config.line_length:
            settings.append(f"line length: {tool_config.line_length}")
        if tool_config.target_version:
            settings.append(f"target version: {tool_config.target_version}")
        if tool_config.include_patterns:
            settings.append(f"includes: {', '.join(tool_config.include_patterns[:3])}{'...' if len(tool_config.include_patterns) > 3 else ''}")
        if tool_config.exclude_patterns:
            settings.append(f"excludes: {', '.join(tool_config.exclude_patterns[:3])}{'...' if len(tool_config.exclude_patterns) > 3 else ''}")

        if settings:
            lines.append(f"  - {'; '.join(settings)}")

        # Additional settings (show count if many)
        additional_settings = {k: v for k, v in tool_config.settings.items()
                             if k not in ['line-length', 'max-line-length', 'target-version', 'include', 'exclude']}

        if additional_settings:
            if len(additional_settings) <= 3:
                for key, value in list(additional_settings.items())[:3]:
                    lines.append(f"  - {key}: `{value}`")
            else:
                lines.append(f"  - {len(additional_settings)} additional settings configured")

        return "\n".join(lines)

    def generate_cli_overview(self) -> str:
        """Generate CLI usage documentation section."""
        if not self.cli_analysis or not self.cli_analysis.interfaces:
            return ""

        output = []
        output.append("## 🖥️ Command Line Interface")
        output.append("")

        # Summary
        frameworks = list(self.cli_analysis.detected_frameworks)
        if frameworks:
            framework_names = [f.value for f in frameworks]
            output.append(f"**Detected CLI Frameworks:** {', '.join(framework_names)}")
            output.append("")

        # Entry points
        if self.cli_analysis.entry_points:
            output.append("### Entry Points")
            output.append("")
            for name, target in self.cli_analysis.entry_points.items():
                output.append(f"- **`{name}`** → `{target}`")
            output.append("")

        # CLI interfaces
        for interface in self.cli_analysis.interfaces:
            output.append(self._format_cli_interface(interface))

        # Configuration files
        if self.cli_analysis.configuration_files:
            output.append("### Configuration Files")
            output.append("")
            output.append("The following configuration files were detected:")
            output.append("")
            for config_file in self.cli_analysis.configuration_files:
                output.append(f"- `{config_file}`")
            output.append("")

        # Environment variables
        if self.cli_analysis.environment_variables:
            output.append("### Environment Variables")
            output.append("")
            output.append("The following environment variables may be used:")
            output.append("")
            for env_var in self.cli_analysis.environment_variables:
                output.append(f"- `{env_var}`")
            output.append("")

        # Show any errors or warnings
        if self.cli_analysis.errors:
            output.append("### ⚠️ CLI Analysis Errors")
            output.append("")
            for error in self.cli_analysis.errors:
                output.append(f"- {error}")
            output.append("")

        if self.cli_analysis.warnings:
            output.append("### ⚠️ CLI Analysis Warnings")
            output.append("")
            for warning in self.cli_analysis.warnings:
                output.append(f"- {warning}")
            output.append("")

        output.append("---")
        output.append("")

        return "\n".join(output)

    def _format_cli_interface(self, interface) -> str:
        """Format a CLI interface for markdown output."""
        try:
            from .cli_analyzer import CLIFramework, ArgumentType
        except ImportError:
            from cli_analyzer import CLIFramework, ArgumentType

        output = []

        # Interface header
        framework_name = interface.framework.value.title()
        output.append(f"### {framework_name} Interface: {interface.name}")
        output.append("")

        # Description
        if interface.description:
            output.append(f"**Description:** {interface.description}")
            output.append("")

        # Help text
        if interface.help_text and interface.help_text != interface.description:
            output.append("**Help:**")
            output.append("")
            for line in interface.help_text.strip().split('\n'):
                output.append(f"> {line}")
            output.append("")

        # Module and main function info
        if interface.module_path:
            output.append(f"**Module:** `{interface.module_path}`")
        if interface.main_function:
            output.append(f"**Main Function:** `{interface.main_function}`")
        if interface.module_path or interface.main_function:
            output.append("")

        # Global arguments
        if interface.global_arguments:
            output.append("**Global Options:**")
            output.append("")
            for arg in interface.global_arguments:
                output.append(self._format_cli_argument(arg, ""))
                output.append("")

        # Commands
        if interface.commands:
            if len(interface.commands) == 1 and not interface.commands[0].subcommands:
                # Single command interface
                command = interface.commands[0]
                if command.arguments:
                    output.append("**Arguments:**")
                    output.append("")
                    for arg in command.arguments:
                        output.append(self._format_cli_argument(arg, ""))
                        output.append("")
            else:
                # Multi-command interface
                output.append("**Commands:**")
                output.append("")
                for command in interface.commands:
                    output.append(self._format_cli_command(command))
                    output.append("")

        # Usage examples
        if interface.usage_examples:
            output.append("**Usage Examples:**")
            output.append("")
            output.append("```bash")
            for example in interface.usage_examples:
                output.append(example)
            output.append("```")
            output.append("")

        return "\n".join(output)

    def _format_cli_command(self, command, indent: str = "") -> str:
        """Format a CLI command for markdown output."""
        output = []

        # Command header
        output.append(f"{indent}#### `{command.name}`")
        output.append("")

        # Description
        if command.description:
            output.append(f"{indent}*{command.description}*")
            output.append("")

        # Help text (if different from description)
        if command.help_text and command.help_text != command.description:
            help_lines = command.help_text.strip().split('\n')
            if len(help_lines) > 1:
                output.append(f"{indent}<details>")
                output.append(f"{indent}<summary>Show detailed help</summary>")
                output.append("")
                output.append(f"{indent}```")
                for line in help_lines:
                    output.append(f"{indent}{line}")
                output.append(f"{indent}```")
                output.append(f"{indent}</details>")
                output.append("")

        # Function info
        if command.function_name:
            output.append(f"{indent}**Function:** `{command.function_name}`")
        if command.module_path:
            output.append(f"{indent}**Module:** `{command.module_path}`")
        if command.function_name or command.module_path:
            output.append("")

        # Arguments
        if command.arguments:
            # Separate by type
            positional_args = [arg for arg in command.arguments if arg.arg_type.value == "positional"]
            optional_args = [arg for arg in command.arguments if arg.arg_type.value == "optional"]
            flags = [arg for arg in command.arguments if arg.arg_type.value == "flag"]

            if positional_args:
                output.append(f"{indent}**Arguments:**")
                output.append("")
                for arg in positional_args:
                    output.append(self._format_cli_argument(arg, indent))
                    output.append("")

            if optional_args:
                output.append(f"{indent}**Options:**")
                output.append("")
                for arg in optional_args:
                    output.append(self._format_cli_argument(arg, indent))
                    output.append("")

            if flags:
                output.append(f"{indent}**Flags:**")
                output.append("")
                for arg in flags:
                    output.append(self._format_cli_argument(arg, indent))
                    output.append("")

        # Subcommands
        if command.subcommands:
            output.append(f"{indent}**Subcommands:**")
            output.append("")
            for subcommand in command.subcommands:
                sub_output = self._format_cli_command(subcommand, indent + "  ")
                output.append(sub_output)

        # Examples
        if command.examples:
            output.append(f"{indent}**Examples:**")
            output.append("")
            output.append(f"{indent}```bash")
            for example in command.examples:
                output.append(f"{indent}{example}")
            output.append(f"{indent}```")
            output.append("")

        return "\n".join(output)

    def _format_cli_argument(self, arg, indent: str = "") -> str:
        """Format a CLI argument for markdown output."""
        parts = []

        # Name with forms
        name_parts = []
        if arg.short_form:
            name_parts.append(f"`{arg.short_form}`")
        if arg.long_form:
            name_parts.append(f"`{arg.long_form}`")
        if not name_parts:
            name_parts.append(f"`{arg.name}`")

        name_str = ", ".join(name_parts)

        # Type information
        type_info = ""
        if arg.type_name:
            type_info = f" *({arg.type_name})*"

        # Required/optional indicator
        required_str = " **[required]**" if arg.required else ""

        # Put together the main line
        parts.append(f"{indent}- **{name_str}**{type_info}{required_str}")

        # Help text
        if arg.help_text:
            parts.append(f"{indent}  {arg.help_text}")

        # Default value
        if arg.default_value is not None:
            parts.append(f"{indent}  *Default: `{arg.default_value}`*")

        # Choices
        if arg.choices:
            choices_str = ", ".join([f"`{choice}`" for choice in arg.choices])
            parts.append(f"{indent}  *Choices: {choices_str}*")

        # Additional details
        details = []
        if arg.metavar:
            details.append(f"metavar: `{arg.metavar}`")
        if arg.dest:
            details.append(f"dest: `{arg.dest}`")
        if arg.action:
            details.append(f"action: `{arg.action}`")
        if arg.nargs:
            details.append(f"nargs: `{arg.nargs}`")

        if details:
            parts.append(f"{indent}  *{', '.join(details)}*")

        return "\n".join(parts)

    def generate_summary(self) -> str:
        """Generate summary section."""
        output = []

        output.append("## 📊 Project Summary")
        output.append("")
        output.append(f"- **Modules:** {self.stats['modules']}")
        output.append(f"- **Classes:** {self.stats['classes']}")
        output.append(f"- **Functions:** {self.stats['functions']}")
        output.append(f"- **Methods:** {self.stats['methods']}")
        output.append("")

        # Documentation coverage
        if self.stats["classes"] > 0:
            class_doc_pct = (
                self.stats["documented_classes"] / self.stats["classes"]
            ) * 100
            output.append(
                f"- **Documented Classes:** {self.stats['documented_classes']}/{self.stats['classes']} ({class_doc_pct:.1f}%)"
            )

        if self.stats["functions"] > 0:
            func_doc_pct = (
                self.stats["documented_functions"] / self.stats["functions"]
            ) * 100
            output.append(
                f"- **Documented Functions:** {self.stats['documented_functions']}/{self.stats['functions']} ({func_doc_pct:.1f}%)"
            )

        if self.stats["methods"] > 0:
            method_doc_pct = (
                self.stats["documented_methods"] / self.stats["methods"]
            ) * 100
            output.append(
                f"- **Documented Methods:** {self.stats['documented_methods']}/{self.stats['methods']} ({method_doc_pct:.1f}%)"
            )

        output.append("")
        output.append("---")
        output.append("")

        return "\n".join(output)

    def generate(self) -> str:
        """Generate the complete markdown report."""
        output = []

        # Header
        project_name = self.analyzer.target_dir.name or "Python Project"
        output.append(f"# 🐍 Python Project Quick Look: {project_name}")
        output.append("")
        output.append(f"*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        output.append("")

        # Visual overview (diagrams)
        visual_overview = self.generate_visual_overview()
        if visual_overview:
            output.append(visual_overview)

        # Project Overview (if context available)
        overview = self.generate_project_overview()
        if overview:
            output.append(overview)

        # Dependency Analysis
        dependency_overview = self.generate_dependency_overview()
        if dependency_overview:
            output.append(dependency_overview)

        # CLI Analysis
        cli_overview = self.generate_cli_overview()
        if cli_overview:
            output.append(cli_overview)

        # Configuration Analysis
        config_overview = self.generate_configuration_overview()
        if config_overview:
            output.append(config_overview)

        # Summary
        output.append(self.generate_summary())

        # Table of Contents
        if len(self.analyzer.modules) > 5:
            output.append("## 📑 Table of Contents")
            output.append("")
            for module in self.analyzer.modules:
                output.append(
                    f"- [{module.name}](#{module.name.replace('.', '').lower()})"
                )
            output.append("")
            output.append("---")
            output.append("")

        # Module details
        for module in self.analyzer.modules:
            output.append(self.format_module(module))

        # Footer
        output.append("---")
        output.append("")
        output.append("*Report generated by Python Quick Look Tool*")

        # Add asset statistics if we have any assets
        if self.asset_manager:
            stats = self.asset_manager.get_asset_stats()
            if stats["total_files"] > 0:
                output.append("")
                output.append(f"*Assets: {stats['total_files']} files ({stats['total_size_mb']} MB)*")

        return "\n".join(output)

    def save_report(self, filename: str = "report.md") -> Path:
        """Generate and save the report to a file.

        Args:
            filename: Name of the report file

        Returns:
            Path to the saved report file
        """
        report_content = self.generate()
        report_path = self.output_dir / filename

        try:
            # Ensure output directory exists
            self.output_dir.mkdir(parents=True, exist_ok=True)

            # Write the report
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report_content)

            logger.info(f"Report saved to: {report_path}")

            # Log asset information
            if self.asset_manager:
                stats = self.asset_manager.get_asset_stats()
                if stats["total_files"] > 0:
                    logger.info(f"Generated {stats['total_files']} asset files")

            return report_path

        except Exception as e:
            logger.error(f"Failed to save report to {report_path}: {e}")
            raise

    def cleanup_assets(self) -> None:
        """Clean up generated assets."""
        if self.asset_manager:
            self.asset_manager.cleanup()
