"""
CLI Pattern Analyzer for Python Quick Look Tool

Detects and analyzes command-line interface patterns in Python projects,
supporting multiple CLI frameworks like argparse, click, typer, and fire.
"""

import ast
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from .python_quicklook import ModuleInfo

logger = logging.getLogger(__name__)


class CLIFramework(Enum):
    """Supported CLI frameworks."""
    ARGPARSE = "argparse"
    CLICK = "click"
    TYPER = "typer"
    FIRE = "fire"
    DOCOPT = "docopt"
    CEMENT = "cement"
    UNKNOWN = "unknown"


class ArgumentType(Enum):
    """Types of CLI arguments."""
    POSITIONAL = "positional"
    OPTIONAL = "optional"
    FLAG = "flag"
    SUBCOMMAND = "subcommand"


@dataclass
class CLIArgument:
    """Represents a single CLI argument, option, or flag."""

    name: str
    arg_type: ArgumentType
    help_text: Optional[str] = None
    default_value: Optional[str] = None
    required: bool = False
    choices: Optional[List[str]] = None
    metavar: Optional[str] = None
    dest: Optional[str] = None
    action: Optional[str] = None
    nargs: Optional[Union[str, int]] = None
    type_name: Optional[str] = None
    short_form: Optional[str] = None
    long_form: Optional[str] = None


@dataclass
class CLICommand:
    """Represents a CLI command or subcommand."""

    name: str
    description: Optional[str] = None
    help_text: Optional[str] = None
    arguments: List[CLIArgument] = field(default_factory=list)
    subcommands: List['CLICommand'] = field(default_factory=list)
    function_name: Optional[str] = None
    module_path: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)


@dataclass
class CLIInterface:
    """Represents a complete CLI interface."""

    name: str
    framework: CLIFramework
    description: Optional[str] = None
    version: Optional[str] = None
    commands: List[CLICommand] = field(default_factory=list)
    global_arguments: List[CLIArgument] = field(default_factory=list)
    entry_points: List[str] = field(default_factory=list)
    usage_examples: List[str] = field(default_factory=list)
    module_path: Optional[str] = None
    main_function: Optional[str] = None
    help_text: Optional[str] = None


@dataclass
class CLIAnalysisResult:
    """Results of CLI pattern analysis."""

    interfaces: List[CLIInterface] = field(default_factory=list)
    detected_frameworks: Set[CLIFramework] = field(default_factory=set)
    entry_points: Dict[str, str] = field(default_factory=dict)
    configuration_files: List[str] = field(default_factory=list)
    environment_variables: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class CLIPatternDetector:
    """Detects CLI framework usage patterns in AST nodes."""

    def __init__(self):
        self.framework_imports = {
            CLIFramework.ARGPARSE: ['argparse'],
            CLIFramework.CLICK: ['click'],
            CLIFramework.TYPER: ['typer'],
            CLIFramework.FIRE: ['fire'],
            CLIFramework.DOCOPT: ['docopt'],
            CLIFramework.CEMENT: ['cement']
        }

    def detect_framework_from_imports(self, module_info: 'ModuleInfo') -> Set[CLIFramework]:
        """Detect CLI frameworks from module imports."""
        detected = set()

        for import_stmt in module_info.imports:
            import_lower = import_stmt.lower()

            for framework, import_names in self.framework_imports.items():
                for import_name in import_names:
                    if (f'import {import_name}' in import_lower or
                        f'from {import_name}' in import_lower):
                        detected.add(framework)

        return detected

    def detect_framework_from_ast(self, tree: ast.AST) -> Set[CLIFramework]:
        """Detect CLI frameworks from AST analysis."""
        detected = set()

        for node in ast.walk(tree):
            # Look for specific patterns
            if isinstance(node, ast.Call):
                # ArgumentParser creation
                if (isinstance(node.func, ast.Attribute) and
                    node.func.attr == 'ArgumentParser'):
                    detected.add(CLIFramework.ARGPARSE)

                # Click decorators
                elif (isinstance(node.func, ast.Attribute) and
                      hasattr(node.func, 'value') and
                      isinstance(node.func.value, ast.Name) and
                      node.func.value.id == 'click'):
                    detected.add(CLIFramework.CLICK)

                # Fire usage
                elif (isinstance(node.func, ast.Attribute) and
                      node.func.attr == 'Fire'):
                    detected.add(CLIFramework.FIRE)

            # Look for decorators
            elif isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    decorator_name = self._get_decorator_name(decorator)
                    if 'click.' in decorator_name:
                        detected.add(CLIFramework.CLICK)
                    elif 'typer.' in decorator_name:
                        detected.add(CLIFramework.TYPER)

        return detected

    def _get_decorator_name(self, decorator: ast.expr) -> str:
        """Extract decorator name from AST node."""
        try:
            return ast.unparse(decorator)
        except Exception:
            return ""


class ArgparseAnalyzer:
    """Analyzes argparse-based CLI patterns."""

    def analyze_module(self, module_info: 'ModuleInfo', tree: ast.AST) -> Optional[CLIInterface]:
        """Analyze argparse patterns in a module."""
        try:
            # Look for ArgumentParser creation and usage
            parser_vars = self._find_argument_parsers(tree)
            if not parser_vars:
                return None

            interface = CLIInterface(
                name=module_info.name,
                framework=CLIFramework.ARGPARSE,
                module_path=module_info.path
            )

            # Analyze each parser
            for parser_var in parser_vars:
                self._analyze_parser(tree, parser_var, interface)

            # Extract main function if present
            main_func = self._find_main_function(tree)
            if main_func:
                interface.main_function = main_func

            return interface if interface.commands or interface.global_arguments else None

        except Exception as e:
            logger.warning(f"Error analyzing argparse patterns in {module_info.name}: {e}")
            return None

    def _find_argument_parsers(self, tree: ast.AST) -> List[str]:
        """Find ArgumentParser variable names."""
        parsers = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (isinstance(target, ast.Name) and
                        isinstance(node.value, ast.Call)):

                        call_name = self._get_call_name(node.value)
                        if 'ArgumentParser' in call_name:
                            parsers.append(target.id)

        return parsers

    def _analyze_parser(self, tree: ast.AST, parser_var: str, interface: CLIInterface) -> None:
        """Analyze a specific ArgumentParser variable."""
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and
                isinstance(node.func, ast.Attribute) and
                isinstance(node.func.value, ast.Name) and
                node.func.value.id == parser_var):

                method_name = node.func.attr

                if method_name == 'add_argument':
                    arg = self._parse_add_argument(node)
                    if arg:
                        interface.global_arguments.append(arg)

                elif method_name == 'add_subparsers':
                    subcommands = self._parse_subparsers(tree, node)
                    interface.commands.extend(subcommands)

    def _parse_add_argument(self, node: ast.Call) -> Optional[CLIArgument]:
        """Parse an add_argument call."""
        try:
            args = []
            kwargs = {}

            # Extract positional arguments
            for arg in node.args:
                if isinstance(arg, ast.Constant):
                    args.append(arg.value)

            # Extract keyword arguments
            for keyword in node.keywords:
                try:
                    if isinstance(keyword.value, ast.Constant):
                        kwargs[keyword.arg] = keyword.value.value
                    elif isinstance(keyword.value, ast.List):
                        kwargs[keyword.arg] = [
                            item.value for item in keyword.value.elts
                            if isinstance(item, ast.Constant)
                        ]
                    else:
                        kwargs[keyword.arg] = ast.unparse(keyword.value)
                except Exception:
                    continue

            if not args:
                return None

            # Determine argument type and name
            name = args[0]
            if name.startswith('-'):
                arg_type = ArgumentType.FLAG if kwargs.get('action') in ['store_true', 'store_false'] else ArgumentType.OPTIONAL
                long_form = name if name.startswith('--') else None
                short_form = name if name.startswith('-') and not name.startswith('--') else None

                # Check for both short and long forms
                if len(args) > 1:
                    for arg in args[1:]:
                        if arg.startswith('--'):
                            long_form = arg
                        elif arg.startswith('-'):
                            short_form = arg
            else:
                arg_type = ArgumentType.POSITIONAL
                long_form = None
                short_form = None

            return CLIArgument(
                name=name,
                arg_type=arg_type,
                help_text=kwargs.get('help'),
                default_value=str(kwargs.get('default')) if kwargs.get('default') is not None else None,
                required=kwargs.get('required', False),
                choices=kwargs.get('choices'),
                metavar=kwargs.get('metavar'),
                dest=kwargs.get('dest'),
                action=kwargs.get('action'),
                nargs=kwargs.get('nargs'),
                type_name=str(kwargs.get('type', '')),
                short_form=short_form,
                long_form=long_form
            )

        except Exception as e:
            logger.debug(f"Error parsing add_argument call: {e}")
            return None

    def _parse_subparsers(self, tree: ast.AST, subparsers_node: ast.Call) -> List[CLICommand]:
        """Parse subparser definitions."""
        commands = []
        # This is a simplified implementation
        # In practice, you'd need to track subparser variables and their add_parser calls
        return commands

    def _find_main_function(self, tree: ast.AST) -> Optional[str]:
        """Find the main function name."""
        for node in ast.walk(tree):
            if (isinstance(node, ast.FunctionDef) and
                node.name == 'main'):
                return 'main'
            elif (isinstance(node, ast.If) and
                  isinstance(node.test, ast.Compare) and
                  len(node.test.left) and
                  isinstance(node.test.left, ast.Name) and
                  node.test.left.id == '__name__'):
                # Look for function calls in the if __name__ == '__main__' block
                for child in ast.walk(node):
                    if (isinstance(child, ast.Call) and
                        isinstance(child.func, ast.Name)):
                        return child.func.id
        return None

    def _get_call_name(self, node: ast.Call) -> str:
        """Extract the name of a function call."""
        try:
            return ast.unparse(node.func)
        except Exception:
            return ""


class ClickAnalyzer:
    """Analyzes Click-based CLI patterns."""

    def analyze_module(self, module_info: 'ModuleInfo', tree: ast.AST) -> Optional[CLIInterface]:
        """Analyze Click patterns in a module."""
        try:
            click_functions = self._find_click_functions(tree)
            if not click_functions:
                return None

            interface = CLIInterface(
                name=module_info.name,
                framework=CLIFramework.CLICK,
                module_path=module_info.path
            )

            # Analyze Click commands and groups
            commands = []
            for func_name, func_node in click_functions.items():
                command = self._analyze_click_function(func_node)
                if command:
                    command.function_name = func_name
                    commands.append(command)

            interface.commands = commands

            # Find the main group or command
            main_command = self._find_main_click_command(commands)
            if main_command:
                interface.description = main_command.description
                interface.help_text = main_command.help_text

            return interface if commands else None

        except Exception as e:
            logger.warning(f"Error analyzing Click patterns in {module_info.name}: {e}")
            return None

    def _find_click_functions(self, tree: ast.AST) -> Dict[str, ast.FunctionDef]:
        """Find functions with Click decorators."""
        click_functions = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    decorator_name = self._get_decorator_name(decorator)
                    if any(click_pattern in decorator_name.lower()
                           for click_pattern in ['click.', '@click', 'command', 'group']):
                        click_functions[node.name] = node
                        break

        return click_functions

    def _analyze_click_function(self, func_node: ast.FunctionDef) -> Optional[CLICommand]:
        """Analyze a Click-decorated function."""
        try:
            command = CLICommand(name=func_node.name)

            # Extract docstring
            docstring = ast.get_docstring(func_node)
            if docstring:
                # First line is typically the description
                lines = docstring.strip().split('\n')
                command.description = lines[0]
                if len(lines) > 1:
                    command.help_text = docstring

            # Analyze decorators for options and arguments
            decorators = []
            arguments = []

            for decorator in func_node.decorator_list:
                decorator_name = self._get_decorator_name(decorator)
                decorators.append(decorator_name)

                # Parse Click options and arguments
                if 'option' in decorator_name.lower():
                    arg = self._parse_click_option(decorator)
                    if arg:
                        arguments.append(arg)
                elif 'argument' in decorator_name.lower():
                    arg = self._parse_click_argument(decorator)
                    if arg:
                        arguments.append(arg)

            command.decorators = decorators
            command.arguments = arguments

            return command

        except Exception as e:
            logger.debug(f"Error analyzing Click function {func_node.name}: {e}")
            return None

    def _parse_click_option(self, decorator: ast.expr) -> Optional[CLIArgument]:
        """Parse a Click @option decorator."""
        try:
            if isinstance(decorator, ast.Call):
                args = []
                kwargs = {}

                # Extract arguments
                for arg in decorator.args:
                    if isinstance(arg, ast.Constant):
                        args.append(arg.value)

                # Extract keyword arguments
                for keyword in decorator.keywords:
                    if isinstance(keyword.value, ast.Constant):
                        kwargs[keyword.arg] = keyword.value.value

                if args:
                    name = args[0]
                    return CLIArgument(
                        name=name,
                        arg_type=ArgumentType.FLAG if kwargs.get('is_flag') else ArgumentType.OPTIONAL,
                        help_text=kwargs.get('help'),
                        default_value=str(kwargs.get('default')) if kwargs.get('default') is not None else None,
                        required=kwargs.get('required', False),
                        type_name=str(kwargs.get('type', '')),
                        long_form=name if name.startswith('--') else None,
                        short_form=name if name.startswith('-') and not name.startswith('--') else None
                    )
        except Exception as e:
            logger.debug(f"Error parsing Click option: {e}")

        return None

    def _parse_click_argument(self, decorator: ast.expr) -> Optional[CLIArgument]:
        """Parse a Click @argument decorator."""
        try:
            if isinstance(decorator, ast.Call):
                args = []
                kwargs = {}

                for arg in decorator.args:
                    if isinstance(arg, ast.Constant):
                        args.append(arg.value)

                for keyword in decorator.keywords:
                    if isinstance(keyword.value, ast.Constant):
                        kwargs[keyword.arg] = keyword.value.value

                if args:
                    name = args[0]
                    return CLIArgument(
                        name=name,
                        arg_type=ArgumentType.POSITIONAL,
                        help_text=kwargs.get('help'),
                        required=kwargs.get('required', True),
                        type_name=str(kwargs.get('type', ''))
                    )
        except Exception as e:
            logger.debug(f"Error parsing Click argument: {e}")

        return None

    def _find_main_click_command(self, commands: List[CLICommand]) -> Optional[CLICommand]:
        """Find the main Click command (usually a group)."""
        # Look for commands with 'main', 'cli', or 'app' in the name
        for command in commands:
            if command.name.lower() in ['main', 'cli', 'app']:
                return command

        # Return the first command if no main found
        return commands[0] if commands else None

    def _get_decorator_name(self, decorator: ast.expr) -> str:
        """Extract decorator name."""
        try:
            return ast.unparse(decorator)
        except Exception:
            return ""


class TyperAnalyzer:
    """Analyzes Typer-based CLI patterns."""

    def analyze_module(self, module_info: 'ModuleInfo', tree: ast.AST) -> Optional[CLIInterface]:
        """Analyze Typer patterns in a module."""
        try:
            # Typer is similar to Click but uses type hints extensively
            typer_functions = self._find_typer_functions(tree)
            if not typer_functions:
                return None

            interface = CLIInterface(
                name=module_info.name,
                framework=CLIFramework.TYPER,
                module_path=module_info.path
            )

            commands = []
            for func_name, func_node in typer_functions.items():
                command = self._analyze_typer_function(func_node)
                if command:
                    command.function_name = func_name
                    commands.append(command)

            interface.commands = commands
            return interface if commands else None

        except Exception as e:
            logger.warning(f"Error analyzing Typer patterns in {module_info.name}: {e}")
            return None

    def _find_typer_functions(self, tree: ast.AST) -> Dict[str, ast.FunctionDef]:
        """Find functions with Typer decorators or app.command decorators."""
        typer_functions = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check for direct typer decorators or app.command style
                for decorator in node.decorator_list:
                    decorator_name = self._get_decorator_name(decorator)
                    if any(pattern in decorator_name.lower()
                           for pattern in ['typer.', 'app.command', '@typer']):
                        typer_functions[node.name] = node
                        break

        return typer_functions

    def _analyze_typer_function(self, func_node: ast.FunctionDef) -> Optional[CLICommand]:
        """Analyze a Typer function using type hints and defaults."""
        try:
            command = CLICommand(name=func_node.name)

            # Extract docstring
            docstring = ast.get_docstring(func_node)
            if docstring:
                lines = docstring.strip().split('\n')
                command.description = lines[0]
                if len(lines) > 1:
                    command.help_text = docstring

            # Analyze function arguments with type hints
            arguments = []
            for arg in func_node.args.args:
                cli_arg = self._parse_typer_argument(arg, func_node)
                if cli_arg:
                    arguments.append(cli_arg)

            command.arguments = arguments
            return command

        except Exception as e:
            logger.debug(f"Error analyzing Typer function {func_node.name}: {e}")
            return None

    def _parse_typer_argument(self, arg: ast.arg, func_node: ast.FunctionDef) -> Optional[CLIArgument]:
        """Parse a Typer function argument with type hints."""
        try:
            name = arg.arg
            type_name = ""
            default_value = None

            # Get type annotation
            if arg.annotation:
                type_name = ast.unparse(arg.annotation)

            # Get default value from function defaults
            defaults = func_node.args.defaults
            if defaults:
                # This is simplified - real implementation would match args to defaults
                try:
                    default_value = ast.unparse(defaults[0])
                except Exception:
                    pass

            # Determine if it's optional based on type hint or default
            is_optional = 'Optional' in type_name or default_value is not None

            return CLIArgument(
                name=name,
                arg_type=ArgumentType.OPTIONAL if is_optional else ArgumentType.POSITIONAL,
                type_name=type_name,
                default_value=default_value
            )

        except Exception as e:
            logger.debug(f"Error parsing Typer argument {arg.arg}: {e}")
            return None

    def _get_decorator_name(self, decorator: ast.expr) -> str:
        """Extract decorator name."""
        try:
            return ast.unparse(decorator)
        except Exception:
            return ""


class FireAnalyzer:
    """Analyzes Python Fire-based CLI patterns."""

    def analyze_module(self, module_info: 'ModuleInfo', tree: ast.AST) -> Optional[CLIInterface]:
        """Analyze Fire patterns in a module."""
        try:
            fire_calls = self._find_fire_calls(tree)
            if not fire_calls:
                return None

            interface = CLIInterface(
                name=module_info.name,
                framework=CLIFramework.FIRE,
                module_path=module_info.path,
                description="Python Fire automatically generates CLI from Python objects"
            )

            # Analyze what's being passed to Fire
            for fire_call in fire_calls:
                self._analyze_fire_target(fire_call, tree, interface)

            return interface if interface.commands else None

        except Exception as e:
            logger.warning(f"Error analyzing Fire patterns in {module_info.name}: {e}")
            return None

    def _find_fire_calls(self, tree: ast.AST) -> List[ast.Call]:
        """Find calls to fire.Fire()."""
        fire_calls = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                call_name = self._get_call_name(node)
                if 'fire.Fire' in call_name or call_name.endswith('Fire'):
                    fire_calls.append(node)

        return fire_calls

    def _analyze_fire_target(self, fire_call: ast.Call, tree: ast.AST, interface: CLIInterface) -> None:
        """Analyze what object/function is passed to Fire."""
        try:
            if fire_call.args:
                target = fire_call.args[0]

                # If it's a class reference, analyze the class
                if isinstance(target, ast.Name):
                    class_node = self._find_class(tree, target.id)
                    if class_node:
                        self._analyze_fire_class(class_node, interface)
                    else:
                        func_node = self._find_function(tree, target.id)
                        if func_node:
                            command = self._analyze_fire_function(func_node)
                            if command:
                                interface.commands.append(command)

        except Exception as e:
            logger.debug(f"Error analyzing Fire target: {e}")

    def _analyze_fire_class(self, class_node: ast.ClassDef, interface: CLIInterface) -> None:
        """Analyze a class that's used with Fire."""
        try:
            # Each public method becomes a command
            for node in class_node.body:
                if (isinstance(node, ast.FunctionDef) and
                    not node.name.startswith('_')):
                    command = self._analyze_fire_function(node)
                    if command:
                        interface.commands.append(command)

        except Exception as e:
            logger.debug(f"Error analyzing Fire class {class_node.name}: {e}")

    def _analyze_fire_function(self, func_node: ast.FunctionDef) -> Optional[CLICommand]:
        """Analyze a function that becomes a Fire command."""
        try:
            command = CLICommand(name=func_node.name)

            # Extract docstring
            docstring = ast.get_docstring(func_node)
            if docstring:
                lines = docstring.strip().split('\n')
                command.description = lines[0]
                command.help_text = docstring

            # Fire automatically creates arguments from function parameters
            arguments = []
            for arg in func_node.args.args:
                if arg.arg != 'self':  # Skip self parameter
                    cli_arg = CLIArgument(
                        name=arg.arg,
                        arg_type=ArgumentType.POSITIONAL,
                        type_name=ast.unparse(arg.annotation) if arg.annotation else None
                    )
                    arguments.append(cli_arg)

            command.arguments = arguments
            return command

        except Exception as e:
            logger.debug(f"Error analyzing Fire function {func_node.name}: {e}")
            return None

    def _find_class(self, tree: ast.AST, class_name: str) -> Optional[ast.ClassDef]:
        """Find a class definition by name."""
        for node in ast.walk(tree):
            if (isinstance(node, ast.ClassDef) and
                node.name == class_name):
                return node
        return None

    def _find_function(self, tree: ast.AST, func_name: str) -> Optional[ast.FunctionDef]:
        """Find a function definition by name."""
        for node in ast.walk(tree):
            if (isinstance(node, ast.FunctionDef) and
                node.name == func_name):
                return node
        return None

    def _get_call_name(self, node: ast.Call) -> str:
        """Extract the name of a function call."""
        try:
            return ast.unparse(node.func)
        except Exception:
            return ""


class CLIAnalyzer:
    """Main CLI pattern analyzer that coordinates different framework analyzers."""

    def __init__(self, target_dir: Path):
        self.target_dir = target_dir
        self.detector = CLIPatternDetector()
        self.argparse_analyzer = ArgparseAnalyzer()
        self.click_analyzer = ClickAnalyzer()
        self.typer_analyzer = TyperAnalyzer()
        self.fire_analyzer = FireAnalyzer()

    def analyze(self, modules: List['ModuleInfo']) -> CLIAnalysisResult:
        """Analyze CLI patterns across all modules."""
        result = CLIAnalysisResult()

        try:
            for module in modules:
                self._analyze_module(module, result)

            # Post-process results
            self._extract_entry_points(result)
            self._find_configuration_patterns(result)
            self._extract_environment_variables(result)

            return result

        except Exception as e:
            logger.error(f"Error during CLI analysis: {e}")
            result.errors.append(f"CLI analysis failed: {e}")
            return result

    def _analyze_module(self, module_info: 'ModuleInfo', result: CLIAnalysisResult) -> None:
        """Analyze a single module for CLI patterns."""
        try:
            # Load and parse the module
            module_path = self.target_dir / module_info.path
            if not module_path.exists():
                return

            with open(module_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)

            # Detect frameworks
            frameworks_from_imports = self.detector.detect_framework_from_imports(module_info)
            frameworks_from_ast = self.detector.detect_framework_from_ast(tree)

            detected_frameworks = frameworks_from_imports | frameworks_from_ast
            result.detected_frameworks.update(detected_frameworks)

            # Analyze each detected framework
            for framework in detected_frameworks:
                interface = None

                if framework == CLIFramework.ARGPARSE:
                    interface = self.argparse_analyzer.analyze_module(module_info, tree)
                elif framework == CLIFramework.CLICK:
                    interface = self.click_analyzer.analyze_module(module_info, tree)
                elif framework == CLIFramework.TYPER:
                    interface = self.typer_analyzer.analyze_module(module_info, tree)
                elif framework == CLIFramework.FIRE:
                    interface = self.fire_analyzer.analyze_module(module_info, tree)
                # TODO: Add docopt, cement analyzers if needed

                if interface:
                    result.interfaces.append(interface)

        except Exception as e:
            logger.warning(f"Error analyzing module {module_info.name}: {e}")
            result.warnings.append(f"Could not analyze {module_info.name}: {e}")

    def _extract_entry_points(self, result: CLIAnalysisResult) -> None:
        """Extract entry points from pyproject.toml or setup.py."""
        try:
            # Check for pyproject.toml
            pyproject_path = self.target_dir / "pyproject.toml"
            if pyproject_path.exists():
                self._parse_pyproject_entry_points(pyproject_path, result)

            # Check for setup.py
            setup_path = self.target_dir / "setup.py"
            if setup_path.exists():
                self._parse_setup_entry_points(setup_path, result)

        except Exception as e:
            logger.debug(f"Error extracting entry points: {e}")

    def _parse_pyproject_entry_points(self, pyproject_path: Path, result: CLIAnalysisResult) -> None:
        """Parse entry points from pyproject.toml."""
        try:
            import tomllib  # Python 3.11+
        except ImportError:
            try:
                import tomli as tomllib  # Fallback for older Python
            except ImportError:
                try:
                    import toml as tomllib  # Another fallback
                    # toml library has different API
                    with open(pyproject_path, 'r') as f:
                        data = tomllib.load(f)

                    # Look for console scripts
                    scripts = data.get('project', {}).get('scripts', {})
                    for name, target in scripts.items():
                        result.entry_points[name] = target
                    return
                except ImportError:
                    logger.debug("No TOML library available for parsing pyproject.toml")
                    return

        try:
            with open(pyproject_path, 'rb') as f:
                data = tomllib.load(f)

            # Look for console scripts
            scripts = data.get('project', {}).get('scripts', {})
            for name, target in scripts.items():
                result.entry_points[name] = target

        except Exception as e:
            logger.debug(f"Error parsing pyproject.toml: {e}")

    def _parse_setup_entry_points(self, setup_path: Path, result: CLIAnalysisResult) -> None:
        """Parse entry points from setup.py."""
        try:
            with open(setup_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Look for entry_points or console_scripts patterns
            # This is a simplified pattern matching approach
            patterns = [
                r"['\"]console_scripts['\"]:\s*\[(.*?)\]",
                r"console_scripts\s*=\s*\[(.*?)\]"
            ]

            for pattern in patterns:
                matches = re.findall(pattern, content, re.DOTALL)
                for match in matches:
                    # Parse individual entries
                    entries = re.findall(r"['\"]([^'\"]+)\s*=\s*([^'\"]+)['\"]", match)
                    for name, target in entries:
                        result.entry_points[name.strip()] = target.strip()

        except Exception as e:
            logger.debug(f"Error parsing setup.py: {e}")

    def _find_configuration_patterns(self, result: CLIAnalysisResult) -> None:
        """Find configuration file patterns."""
        config_patterns = [
            "config.json", "config.yaml", "config.yml", "config.toml",
            "settings.json", "settings.yaml", "settings.yml",
            ".env", ".env.example", "pyproject.toml", "setup.cfg"
        ]

        for pattern in config_patterns:
            config_path = self.target_dir / pattern
            if config_path.exists():
                result.configuration_files.append(pattern)

    def _extract_environment_variables(self, result: CLIAnalysisResult) -> None:
        """Extract environment variable usage patterns."""
        try:
            # Look through all Python files in the project, not just CLI interfaces
            for py_file in self.target_dir.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Look for os.environ, os.getenv, etc.
                    env_patterns = [
                        r"os\.environ\[['\"]([A-Z_][A-Z0-9_]*)['\"]",
                        r"os\.getenv\(['\"]([A-Z_][A-Z0-9_]*)['\"]",
                        r"os\.environ\.get\(['\"]([A-Z_][A-Z0-9_]*)['\"]",
                        r"environ\.get\(['\"]([A-Z_][A-Z0-9_]*)['\"]"
                    ]

                    for pattern in env_patterns:
                        matches = re.findall(pattern, content)
                        result.environment_variables.extend(matches)

                except Exception as e:
                    logger.debug(f"Error reading file {py_file}: {e}")
                    continue

        except Exception as e:
            logger.debug(f"Error extracting environment variables: {e}")

        # Remove duplicates and sort
        result.environment_variables = sorted(set(result.environment_variables))
