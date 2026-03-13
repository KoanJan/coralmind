# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.8] - 2026-03-14

### Added

- **Global Requirements Context**: Propagate original requirements to each execution step
  - Added `global_requirements` parameter to Executor and Validator
  - Added `GLOBAL_REQUIREMENTS_CONTEXT` prompt template (CN/EN)
  - Helps maintain alignment with overall task goals throughout multi-step execution

- **Material Coverage Validation**: Ensure all materials are used in plan
  - Integrated into `_validate_plan_structure` method
  - Raises `PlanValidationError` if any material is not referenced in plan

- **Plan Generation Retry**: Simple retry mechanism for plan validation failures
  - Added `max_retry_times_for_plan` parameter to Agent (default: 3)

### Changed

- **Scoring System Redesign**: Replaced multi-dimensional scoring with dependency-based rating
  - New sequential evaluation: deliverable type → logic → requirements completion → depth/innovation
  - Clearer grading criteria: Failed(0-2) → Poor(3-4) → Average(5-6) → Good(7-8) → Excellent(9-10)

- **Method Renaming**: `Validator.validate` renamed to `validate_execution` for clarity

## [0.0.7] - 2026-03-12

### Fixed

- **Executor Material Format**: Added material name header in executor messages for better LLM context
  - Before: Material content was passed without context
  - After: Material content is formatted with name header (`# {name}\n\n{content}\n`)

## [0.0.6] - 2026-03-11

### Added

- **Multi-language Prompt System**: Full internationalization support for prompts
  - Added `Language` enum (EN, CN) as public API in model package
  - Created language-specific prompt directories (`en/`, `cn/`)
  - All prompts now support both English and Chinese

### Changed

- **Prompt Architecture Refactoring**: Complete restructure for better maintainability
  - `name.py`: `PromptName` and `PromptTemplateName` enums for type-safe prompt access
  - `static.py`: Static prompts (PLAN_STANDARD, EVALUATION_STANDARD)
  - `template.py`: Template prompts requiring formatting
  - `func.py`: Complex build functions (build_score_messages, build_validation_messages)
  - Removed old `llm.py`, `worker.py`, `evaluation_standard.py`, `plan_standard.py` from prompts

- **Type Safety**: Replaced string-based prompt names with enums
  - `PromptName` for static prompts (used with `get_prompt()`)
  - `PromptTemplateName` for template prompts (used with `build_prompt()`)

- **Dependency Decoupling**: `Language` enum moved from prompts to model package
  - `model.Language` is now the public API
  - `prompts` package uses internal `_get_module_prefix()` for language dispatch

## [0.0.5] - 2026-03-09

### Fixed

- **Planner Prompt Design**: Fixed issue where LLM incorrectly referenced "Final Output Format" as a material
  - Moved output_format to a separate section outside Task Input
  - Added explicit warnings that output_format is NOT a material
  - Added "Materials (Available for input_fields)" label for clarity

### Changed

- **Debug Logging**: Added comprehensive debug logging for main workflow key nodes
  - Agent: task execution, template extraction, plan generation, node execution, orchestration, evaluation
  - Worker: plan generation, validation, execution details
  - OutputFormat: JSON Schema to Pydantic model conversion

## [0.0.4] - 2026-03-08

### Added

- **JSON Schema Support**: New `output_format` module with comprehensive JSON Schema to Pydantic model conversion
  - `json_schema_to_pydantic()` function for dynamic model generation
  - Support for `$defs` and `$ref` references
  - Support for `enum` and `const` types
  - Support for `anyOf`, `oneOf`, `allOf` combination types
  - Support for `null` type and nullable fields
  - Support for string constraints: `minLength`, `maxLength`, `pattern`, `format`
  - Support for numeric constraints: `minimum`, `maximum`, `exclusiveMinimum`, `exclusiveMaximum`, `multipleOf`
  - Support for array constraints: `minItems`, `maxItems`
  - Support for `additionalProperties` control
  - Support for nested objects and arrays

### Changed

- **Breaking**: Renamed `OutputFormater` to `OutputFormatter` (corrected spelling)
- **Breaking**: Renamed `output_formater` attribute to `output_formatter` in `Agent` class
- Improved code style and linting compliance across all modules
- Fixed variable naming: `meterials_names` → `materials_names`, `node_indicies` → `node_indices`

### Fixed

- Documentation typos in README.md and README_CN.md

## [0.0.3] - 2026-03-07

### Added

- Token cost tracking throughout the execution pipeline
- Evaluation flow refactoring for better scoring mechanism

## [0.0.2] - 2026-03-04

### Fixed

- CI/CD pipeline issues

## [0.0.1] - 2026-03-04

### Added

- Initial release with core features:
  - Self-evolving AI Agent framework
  - Intelligent planning with multi-node execution
  - Result validation with rule-based and semantic checks
  - Closed-loop feedback with LLM scoring
  - Persistent storage for task templates and plans
  - ThresholdStrategy for plan reuse optimization
